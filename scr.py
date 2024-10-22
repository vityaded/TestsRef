import os
import re
from app import create_app  # Replace 'your_app_name' with your actual app package name
from flask import current_app
from jinja2 import TemplateSyntaxError
from werkzeug.routing import BuildError

def get_all_routes(app):
    """Get a dictionary of all routes in the app, where keys are short names and values are full endpoint names."""
    routes = {}
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        route_name = endpoint.split('.')[-1]
        routes[route_name] = endpoint
    return routes

def find_and_fix_routes_in_templates(template_dir, all_routes):
    """Scan templates for `url_for` usage and fix incorrect route references."""
    # Regex pattern to match `url_for` usages in Jinja templates
    url_for_pattern = r"\{\{\s*url_for\(\s*['\"]([a-zA-Z0-9_\.]+)['\"]"

    # Walk through all template files in the directory
    for root, _, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                template_path = os.path.join(root, file)
                
                # Read the template file
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Search for all instances of url_for in the template
                matches = re.findall(url_for_pattern, content)

                # For each match, check if it needs to be replaced
                modified_content = content
                for match in matches:
                    short_route = match.split('.')[-1]

                    if short_route in all_routes and match != all_routes[short_route]:
                        print(f"Found incorrect route '{match}' in {template_path}")
                        correct_route = all_routes[short_route]
                        modified_content = re.sub(
                            f"url_for\(['\"]{match}['\"]", 
                            f"url_for('{correct_route}')", 
                            modified_content
                        )
                        print(f"Replaced with '{correct_route}'")

                # If the file was modified, write the changes back
                if modified_content != content:
                    with open(template_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    print(f"Updated routes in {template_path}")

if __name__ == "__main__":
    # Create the application instance
    app = create_app()

    # Ensure you are in the correct context of your Flask app
    with app.app_context():
        # Get all valid routes in the app
        all_routes = get_all_routes(app)
        
        # Print all discovered routes (optional)
        print("Discovered routes:")
        for short_name, full_route in all_routes.items():
            print(f"{short_name}: {full_route}")

        # Get the template directory
        template_directory = os.path.join(current_app.root_path, 'templates')

        # Find and fix routes in templates
        find_and_fix_routes_in_templates(template_directory, all_routes)
