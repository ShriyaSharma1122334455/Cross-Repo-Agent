import os
from dataclasses import dataclass

REQUIRED_ENV_VARS = (
    "GITHUB_APP_ID",
    "GITHUB_APP_PRIVATE_KEY_PATH",
    "GITHUB_WEBHOOK_SECRET",
    "TARGET_ORG",
)


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    github_app_id: str
    github_app_private_key_path: str
    github_webhook_secret: str
    target_org: str
    bedrock_model_cheap: str
    bedrock_model_strong: str
    aws_region: str
    mechanical_fix_confidence_threshold: float
    state_backend: str
    sqlite_path: str
    dynamo_table: str

    @classmethod
    def load(cls) -> "Config":
        missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
        if missing:
            raise ConfigError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )

        return cls(
            github_app_id=os.environ["GITHUB_APP_ID"],
            github_app_private_key_path=os.environ["GITHUB_APP_PRIVATE_KEY_PATH"],
            github_webhook_secret=os.environ["GITHUB_WEBHOOK_SECRET"],
            target_org=os.environ["TARGET_ORG"],
            bedrock_model_cheap=os.environ.get(
                "BEDROCK_MODEL_CHEAP", "anthropic.claude-haiku"
            ),
            bedrock_model_strong=os.environ.get(
                "BEDROCK_MODEL_STRONG", "anthropic.claude-sonnet"
            ),
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            mechanical_fix_confidence_threshold=float(
                os.environ.get("MECHANICAL_FIX_CONFIDENCE_THRESHOLD", "0.8")
            ),
            state_backend=os.environ.get("STATE_BACKEND", "sqlite"),
            sqlite_path=os.environ.get("SQLITE_PATH", ".local/state.db"),
            dynamo_table=os.environ.get("DYNAMO_TABLE", "blast-radius-actions"),
        )
