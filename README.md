# Fortigate 8.0.0 Copilot

## Configuration

[Application settings](src/fortigate_8_0_0_copilot/config.py) use
`pydantic-settings` to read `APP_ENV` and `LOG_LEVEL`.

Create a local `.env` file in the project root from
[.env.example](.env.example) if one does not already exist. The local `.env`
file is ignored by Git.

```dotenv
APP_ENV=development
LOG_LEVEL=INFO
```

Import the shared settings instance:

```python
from fortigate_8_0_0_copilot.config import settings

app_env = settings.app_env
log_level = settings.log_level
```

Environment variables override `.env` values. Missing values default to
`development` and `INFO`. In the source checkout, the `.env` path is resolved
relative to the configuration module, not the working directory. For an
installed deployment, supply settings through environment variables.

`APP_ENV` accepts a string. `LOG_LEVEL` accepts `CRITICAL`, `FATAL`, `ERROR`,
`WARNING`, `WARN`, `INFO`, `DEBUG`, or `NOTSET`; invalid levels raise a Pydantic
validation error. Unrelated `.env` keys are ignored. The shared instance is
loaded once at import time; create `Settings()` to reload configuration.

## Tests

```powershell
uv run python -m unittest discover -s tests -p test_config.py
```