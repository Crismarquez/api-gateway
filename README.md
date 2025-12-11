## API Gateway

This project is an **API Gateway** built with **FastAPI**.  
Its main responsibilities are to expose HTTP endpoints, handle CORS, and validate **Azure Entra ID (Azure AD)** tokens to authenticate and authorize users.

---

## Prerequisites

- **Python** 3.10 or higher
- Access to an **Azure Entra ID (Azure AD)** tenant with a registered application
- `.env` file with the required configuration variables

---

## Installation

1. Clone the repository (if you haven’t already):

```bash
git clone <repository-url>
cd api_gateway
```

2. (Optional but recommended) Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

The main configuration is defined in `app/config/config.py` and is loaded from:

- System environment variables
- `.env` file located in `app/.env`

Key variables for Azure Entra ID authentication:

- **`AZURE_AD_TENANT_ID`**: Azure Entra ID tenant ID.
- **`AZURE_AD_CLIENT_ID`**: Client ID (Application ID) of the registered app.
- **`AZURE_AD_ISSUER`** *(optional)*: Expected token issuer.  
  Default: `https://login.microsoftonline.com/<TENANT_ID>/v2.0`.
- **`AZURE_AD_OPENID_CONFIG_URL`** *(optional)*: OpenID configuration URL.
- **`AZURE_AD_JWKS_URI`** *(optional)*: Direct URL to the JWKS (public keys).
- **`AZURE_AD_AUDIENCE`** *(optional)*: Expected audience (for example `api://<client-id>`).  
  If not set, `AZURE_AD_CLIENT_ID` is used.

Additionally, the `config.py` module:
- Creates and uses `data/` and `logs/` directories at the project root.
- Configures logging (console and files `logs/info.log` and `logs/error.log`).

---

## Project structure

Relevant parts of the API Gateway:

- **`app/main.py`**: FastAPI application entrypoint.
  - Creates the `FastAPI` instance.
  - Configures CORS.
  - Registers routers (currently `auth`).
  - Defines `startup` and `shutdown` events.
- **`app/auth/azure_ad.py`**:
  - Loads Azure Entra ID configuration (`AzureADSettings`).
  - Downloads and caches OpenID configuration and JWKS.
  - Validates JWT tokens (`validate_jwt`).
  - Exposes the `get_current_user_claims` dependency for FastAPI.
  - Builds user information from claims (`build_user_info_from_claims`).
- **`app/routers/auth.py`**:
  - Defines the `/auth` router.
  - Exposes the `GET /auth/me` endpoint that validates the token and returns basic user information.
- **`app/config/config.py`**:
  - Loads environment variables and `.env`.
  - Configures logging and `data` / `logs` paths.

---

## Running locally

From the project root (`api_gateway`), with the virtual environment activated and configuration variables set:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

or using the `if __name__ == "__main__":` block in `app/main.py`:

```bash
python -m app.main
```

The API will typically be available at:  
`http://localhost:8001`

---

## Main endpoints

### `GET /`

- **Description**: Root endpoint that returns a basic HTML response (placeholder) with API information.
- **Authentication**: No token required.

### `GET /auth/me`

- **Full path**: `/auth/me`
- **Description**:
  - Validates the Azure Entra ID token provided in the `Authorization` header.
  - Returns basic information about the authenticated user.
- **Authentication**: Requires a valid Bearer token.
- **Headers**:
  - `Authorization: Bearer <access_or_id_token>`
- **Response (example)**:

```json
{
  "user": {
    "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "name": "User Name",
    "email": "user@domain.com",
    "groups": [
      "group-id-1",
      "group-id-2"
    ]
  }
}
```

---

## Azure Entra ID authentication

The `app/auth/azure_ad.py` module implements the token validation logic:

- Downloads OpenID configuration and JWKS from the tenant to validate the token signature.
- Accepts different combinations of:
  - **issuer** (`iss`): v1 (`https://sts.windows.net/<tenant-id>/`) and v2 (`https://login.microsoftonline.com/<tenant-id>/v2.0`).
  - **audience** (`aud`): value configured in `AZURE_AD_AUDIENCE` or `AZURE_AD_CLIENT_ID`.
- Extracts from the token:
  - User information: `name`, `email` (`preferred_username`, `upn`, `email` or `emails`).
  - Groups: `groups` claim (if configured in the Entra ID app).

To consume this API from a frontend:
1. Obtain an **access token** or **ID token** for this API Gateway application (depending on your permissions configuration).
2. Send the token in the header:

```http
Authorization: Bearer <token>
```

---

## CORS

The CORS middleware is configured in `app/main.py`:

- `allow_origins=["*"]`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

This makes development and testing easier from different origins.  
For production, you should restrict `allow_origins` to trusted domains.

---

## Logging and directories

- Logs are stored in the `logs/` directory at the project root:
  - `logs/info.log`
  - `logs/error.log`
- The `data/` directory is available for application data.
- `RichHandler` is used to improve console output during development.

---

## Tests

The project includes a `tests/` directory (currently empty or under construction).  
Recommended integration tests include:

- Verifying `/auth/me` behavior with valid and invalid tokens.
- Testing error handling for Azure Entra ID configuration issues.

---

## Deployment

This API Gateway can be deployed to any platform that supports Python/FastAPI, for example:

- **Azure App Service**
- **Azure Container Apps / Azure Kubernetes Service (AKS)** using the included `Dockerfile`
- Any other container-compatible platform or Python application host

Production considerations:

- Ensure environment variables (`AZURE_AD_*`) are correctly configured.
- Adjust CORS (`allow_origins`) to match frontend domains.
- Tune workers, timeouts, and logging according to expected load.


