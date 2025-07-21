from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spreadsheet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

# Models
class Cell(db.Model):
    __tablename__ = 'cells'
    
    id = db.Column(db.Integer, primary_key=True)
    cell_id = db.Column(db.String(10), unique=True, nullable=False)  # e.g., 'A1', 'B2'
    value = db.Column(db.String(500), default='')
    formula = db.Column(db.String(500), default='')
    
    def to_dict(self):
        return {
            'cell_id': self.cell_id,
            'value': self.value,
            'formula': self.formula
        }

class CellDependency(db.Model):
    __tablename__ = 'cell_dependencies'
    
    id = db.Column(db.Integer, primary_key=True)
    cell_id = db.Column(db.String(10), db.ForeignKey('cells.cell_id'), nullable=False)
    depends_on = db.Column(db.String(10), nullable=False)  # The cell ID this cell depends on
    
    __table_args__ = (
        db.UniqueConstraint('cell_id', 'depends_on', name='unique_dependency'),
    )

# Helper functions
def get_cell_references(formula):
    """Extract cell references from formula (e.g., '=A1+B2' -> ['A1', 'B2'])"""
    if not formula or not formula.startswith('='):
        return []
    # Simple regex to match cell references like A1, B2, etc.
    return re.findall(r'[A-Za-z]+[0-9]+', formula[1:])

def evaluate_formula(formula, cell_references):
    """Simple formula evaluation (basic arithmetic operations)"""
    if not formula.startswith('='):
        return formula
    
    try:
        # Replace cell references with their values
        expr = formula[1:]
        for ref in cell_references:
            cell = Cell.query.filter_by(cell_id=ref).first()
            if cell and cell.value.isdigit():
                expr = expr.replace(ref, cell.value)
        
        # Basic safety check
        if any(c.isalpha() for c in expr if c not in '+-*/(). '):
            return "#ERROR! Invalid formula"
            
        return str(eval(expr))
    except Exception as e:
        return f"#ERROR! {str(e)}"

def update_dependencies(cell_id, formula):
    """Update dependency relationships for a cell"""
    # Remove existing dependencies
    CellDependency.query.filter_by(cell_id=cell_id).delete()
    
    # Add new dependencies
    for ref in get_cell_references(formula):
        dependency = CellDependency(cell_id=cell_id, depends_on=ref)
        db.session.add(dependency)
    
    db.session.commit()

def get_dependent_cells(cell_id):
    """Get all cells that depend on the given cell"""
    return [d.cell_id for d in CellDependency.query.filter_by(depends_on=cell_id).all()]

def update_cell_value(cell_id, new_value):
    """Update a cell's value and propagate changes to dependent cells"""
    cell = Cell.query.filter_by(cell_id=cell_id).first()
    if not cell:
        return None
    
    cell.value = new_value
    db.session.commit()
    
    # Update all cells that depend on this one
    for dependent_id in get_dependent_cells(cell_id):
        dependent = Cell.query.filter_by(cell_id=dependent_id).first()
        if dependent and dependent.formula:
            refs = get_cell_references(dependent.formula)
            ref_values = {ref: Cell.query.filter_by(cell_id=ref).first().value 
                         for ref in refs if Cell.query.filter_by(cell_id=ref).first()}
            new_value = evaluate_formula(dependent.formula, ref_values)
            update_cell_value(dependent_id, new_value)
    
    return cell

# Routes
@app.route('/api/cells', methods=['GET'])
def get_all_cells():
    cells = Cell.query.all()
    return jsonify([cell.to_dict() for cell in cells])

@app.route('/api/cells/<cell_id>', methods=['GET'])
def get_cell(cell_id):
    cell = Cell.query.filter_by(cell_id=cell_id.upper()).first()
    if not cell:
        return jsonify({'error': 'Cell not found'}), 404
    return jsonify(cell.to_dict())

@app.route('/api/cells/<cell_id>', methods=['PUT'])
def update_cell(cell_id):
    data = request.get_json()
    cell_id = cell_id.upper()
    
    # Validate cell_id format (e.g., A1, B2, etc.)
    if not re.match(r'^[A-Za-z]+[0-9]+$', cell_id):
        return jsonify({'error': 'Invalid cell ID format'}), 400
    
    # Get or create the cell
    cell = Cell.query.filter_by(cell_id=cell_id).first()
    if not cell:
        cell = Cell(cell_id=cell_id)
        db.session.add(cell)
    
    # Update cell data
    if 'value' in data:
        cell.value = str(data['value'])
        cell.formula = ''  # Clear formula if setting direct value
    elif 'formula' in data:
        cell.formula = data['formula']
        refs = get_cell_references(cell.formula)
        
        # Check for circular dependencies
        if cell_id in refs:
            return jsonify({'error': 'Circular reference detected'}), 400
            
        # Check if all references exist
        for ref in refs:
            if not Cell.query.filter_by(cell_id=ref).first():
                return jsonify({'error': f'Reference to undefined cell: {ref}'}), 400
        
        # Evaluate formula
        ref_values = {ref: Cell.query.filter_by(cell_id=ref).first().value for ref in refs}
        cell.value = evaluate_formula(cell.formula, ref_values)
        
        # Update dependencies
        update_dependencies(cell_id, cell.formula)
    
    db.session.commit()
    
    # Propagate changes to dependent cells
    if 'formula' in data:
        for dependent_id in get_dependent_cells(cell_id):
            dependent = Cell.query.filter_by(cell_id=dependent_id).first()
            if dependent and dependent.formula:
                refs = get_cell_references(dependent.formula)
                ref_values = {ref: Cell.query.filter_by(cell_id=ref).first().value 
                             for ref in refs if Cell.query.filter_by(cell_id=ref).first()}
                new_value = evaluate_formula(dependent.formula, ref_values)
                update_cell_value(dependent_id, new_value)
    
    return jsonify(cell.to_dict())

@app.route('/api/cells/<cell_id>', methods=['DELETE'])
def delete_cell(cell_id):
    cell = Cell.query.filter_by(cell_id=cell_id.upper()).first()
    if not cell:
        return jsonify({'error': 'Cell not found'}), 404
    
    # Check if any cells depend on this one
    dependents = get_dependent_cells(cell_id)
    if dependents:
        return jsonify({
            'error': 'Cannot delete cell: other cells depend on it',
            'dependents': dependents
        }), 400
    
    # Remove dependencies and the cell
    CellDependency.query.filter_by(cell_id=cell_id).delete()
    db.session.delete(cell)
    db.session.commit()
    
    return jsonify({'message': 'Cell deleted successfully'})

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)