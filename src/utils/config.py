
# Minimal non-Pydantic config object
# We intentionally avoid Pydantic because it causes import errors
class Settings:
    def __init__(self):
        self.project_name = "Battlefield FDE"
        self.environment = "dev"


settings = Settings()
