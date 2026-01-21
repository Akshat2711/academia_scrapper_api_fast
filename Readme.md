# Academia Scraper API

## How to Run

### Prerequisites
- Python 3.8+
- Virtual Environment (recommended)

### Steps

1.  **Create/Activate Virtual Environment**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**:
    ```bash
    uvicorn app:app --reload
    ```

    The API will be available at `http://localhost:8000`.
    Swagger documentation is available at `http://localhost:8000/docs`.
