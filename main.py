
from routes import auth, user_routes, gameify_routes, guardians_routes
from fastapi_config import app, create_db_and_tables

app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(guardians_routes.router)
app.include_router(gameify_routes.router)
create_db_and_tables()