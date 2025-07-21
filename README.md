# Spreadsheet Cell Management API

A RESTful API for managing spreadsheet cells, their values, formulas, and dependencies.

## Features

- Create, read, update, and delete spreadsheet cells
- Support for formulas with cell references (e.g., `=A1+B2`)
- Automatic dependency tracking and value propagation
- SQLite database for data persistence
- Input validation and error handling

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```

The API will be available at `http://localhost:5000`

## API Endpoints

### Get All Cells
- **URL**: `/api/cells`
- **Method**: `GET`
- **Response**: List of all cells with their values and formulas

### Get Cell
- **URL**: `/api/cells/<cell_id>`
- **Method**: `GET`
- **Parameters**:
  - `cell_id`: The ID of the cell (e.g., A1, B2)
- **Response**: Cell details or 404 if not found

### Update Cell
- **URL**: `/api/cells/<cell_id>`
- **Method**: `PUT`
- **Parameters**:
  - `cell_id`: The ID of the cell (e.g., A1, B2)
- **Request Body**:
  - To set a direct value:
    ```json
    {
      "value": "42"
    }
    ```
  - To set a formula:
    ```json
    {
      "formula": "=A1+B2"
    }
    ```
- **Response**: Updated cell details

### Delete Cell
- **URL**: `/api/cells/<cell_id>`
- **Method**: `DELETE`
- **Parameters**:
  - `cell_id`: The ID of the cell to delete
- **Response**: Success message or error if the cell has dependents

## Examples

### Setting a cell value
```http
PUT /api/cells/A1
Content-Type: application/json

{
  "value": "10"
}
```

### Setting a formula
```http
PUT /api/cells/B1
Content-Type: application/json

{
  "formula": "=A1*2"
}
```

### Getting a cell value
```http
GET /api/cells/B1
```

## Dependencies

- Python 3.7+
- Flask
- Flask-SQLAlchemy
- SQLite (included in Python standard library)

## Error Handling

The API returns appropriate HTTP status codes and JSON error messages for various error conditions, such as:
- 400 Bad Request: Invalid input or formula
- 404 Not Found: Cell not found
- 409 Conflict: Attempt to delete a cell with dependents
