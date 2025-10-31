#!/bin/bash

# This script dynamically corrects the __tablename__ in generated SQLAlchemy models
# to be snake_case. It iterates through all Python files in the schemas/generated
# directory and converts the PascalCase table names to snake_case.

set -e

for file in schemas/generated/*.py; do
  if [ -f "$file" ]; then
    echo "Processing $file..."
    # Use a while loop to read the file line by line
    while IFS= read -r line; do
      # Check if the line contains the __tablename__ declaration
      if [[ "$line" == *__tablename__* ]]; then
        # Extract the PascalCase name from the line
        pascal_case_name=$(echo "$line" | sed -n "s/.*__tablename__ = '\([^']*\)'.*/\1/p")
        # Convert the PascalCase name to snake_case
        snake_case_name=$(echo "$pascal_case_name" | sed -e 's/\([A-Z]\)/_\1/g' -e 's/^_//' | tr '[:upper:]' '[:lower:]')
        # Replace the PascalCase name with the snake_case name in the file
        sed -i '' "s/__tablename__ = '$pascal_case_name'/__tablename__ = '$snake_case_name'/" "$file"
      fi
    done < "$file"
  fi
done

echo "SQLA table names have been corrected."
