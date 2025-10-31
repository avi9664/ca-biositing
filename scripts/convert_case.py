import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def pascal_to_snake(name):
    """Converts a PascalCase string to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def process_file(filepath):
    """
    Processes a single Python file to convert PascalCase to snake_case for
    __tablename__ and foreign key references.
    """
    logging.info(f"Processing file: {filepath}")
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except IOError as e:
        logging.error(f"Could not read file {filepath}: {e}")
        return

    original_content = content
    pascal_case_names = set(re.findall(r"__tablename__ = '([^']*)'", content))

    if not pascal_case_names:
        logging.info(f"No __tablename__ found in {filepath}. Skipping.")
        return

    for name in pascal_case_names:
        snake_name = pascal_to_snake(name)
        logging.info(f"Found table: '{name}'. Converting to '{snake_name}'.")

        # 1. Replace __tablename__
        content = content.replace(f"__tablename__ = '{name}'", f"__tablename__ = '{snake_name}'")

        # 2. Replace foreign key references
        # This regex looks for foreign_key='TableName.column'
        fk_pattern = re.compile(f"foreign_key='({name})\\.([^']*)'")
        content = fk_pattern.sub(f"foreign_key='{snake_name}.\\2'", content)

    if content != original_content:
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            logging.info(f"Successfully updated {filepath}.")
        except IOError as e:
            logging.error(f"Could not write to file {filepath}: {e}")
    else:
        logging.info(f"No changes were necessary for {filepath}.")


def main():
    """
    Main function to find and process all generated SQLAlchemy model files.
    """
    generated_dir = os.path.join('schemas', 'generated')
    if not os.path.isdir(generated_dir):
        logging.error(f"Directory not found: {generated_dir}")
        return

    logging.info(f"Starting conversion process in '{generated_dir}'...")
    for filename in os.listdir(generated_dir):
        if filename.endswith('.py'):
            process_file(os.path.join(generated_dir, filename))
    logging.info("Conversion process finished.")

if __name__ == "__main__":
    main()
