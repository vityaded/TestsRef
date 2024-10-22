import os
import shutil

# Define the new folder structure
template_structure = {
    "main": ["index.html", "search_results.html", "book_tests.html"],
    "auth": ["login.html", "signup.html"],
    "tests": ["add_test.html", "edit_test.html", "take_test.html", "learn_test.html"],
    "vocabulary": ["vocabulary.html", "edit_word.html"],
    "admin": ["admin_panel.html"],
    "layouts": ["base.html"],
    "shared": ["csrf_error.html"]
}

# Paths
current_template_folder = "templates"
backup_folder = "templates_backup"

# Create backup of the current template folder before reorganizing
if not os.path.exists(backup_folder):
    shutil.copytree(current_template_folder, backup_folder)
    print(f"Backup created in '{backup_folder}'")

# Create new folder structure
for folder, files in template_structure.items():
    folder_path = os.path.join(current_template_folder, folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

    # Move files to their new locations
    for file_name in files:
        old_file_path = os.path.join(current_template_folder, file_name)
        new_file_path = os.path.join(folder_path, file_name)

        if os.path.exists(old_file_path):
            shutil.move(old_file_path, new_file_path)
            print(f"Moved {file_name} to {folder}")

# Check for any files that were not moved and warn the user
remaining_files = os.listdir(current_template_folder)
if remaining_files:
    print("\nThe following files were not part of the refactoring structure and remain in the root folder:")
    for file in remaining_files:
        print(f"- {file}")
else:
    print("\nAll template files have been successfully moved!")

print("\nTemplate reorganization complete!")
