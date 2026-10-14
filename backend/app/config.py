from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    supabase_url: str
    supabase_service_role_key: str
    stripe_secret_key: str
    stripe_webhook_secret: str

    # Where the deployed frontend lives. Used for CORS and for the
    # Stripe onboarding return/refresh links. Override on Render with
    # a FRONTEND_URL environment variable if the site address changes.
    frontend_url: str = "https://quad-gig.vercel.app"


settings = Settings()
