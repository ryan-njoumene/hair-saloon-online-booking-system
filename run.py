"""Import Function that create App and import all its blueprints"""
from app import create_app

app = create_app()
if __name__ == "__main__":
    app.run(port=5008)
