"""
main.py

Entry point for the BeerOnline application. Run `python3 main.py` to start
the local development server.
"""

from app import app

from app.routes import main_bp
app.register_blueprint(main_bp)

if __name__ == "__main__":
    # Run the Flask development server with live reload enabled
    app.run(host="127.0.0.1", port=5000, debug=True)