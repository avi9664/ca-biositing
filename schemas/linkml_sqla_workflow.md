# Generating SQLAlchemy Models from LinkML Schemas

This document outlines the process of generating SQLAlchemy (SQLA) models from
LinkML schemas and integrating them with Alembic for database migrations.

## 1. Create a LinkML Schema

Create a YAML file (e.g., `my_schema.yaml`) to define your data model. The
schema should include:

- **`id`**: A unique identifier for the schema.
- **`name`**: A human-readable name for the schema.
- **`description`**: A brief description of the schema's purpose.
- **`prefixes`**: A mapping of prefixes to URIs for linked data.
- **`imports`**: A list of other LinkML schemas to import.
- **`classes`**: The main data structures of your model.
- **`slots`**: The properties of your classes.
- **`enums`**: Controlled vocabularies for your slots.

## 2. Generate SQLAlchemy Models

Use the `gen-sqla` command from the `linkml` library to create SQLAlchemy models
from your schema. The following command will generate a Python file containing
your models:

```bash
gen-sqla your_schema.yaml > schemas/generated/your_model.py
```

If your schema imports other schemas, you may want to use the
`--no-mergeimports` flag to avoid including the imported models in the generated
file:

```bash
gen-sqla --no-mergeimports your_schema.yaml > schemas/generated/your_model.py
```

## 3. Convert Table and Foreign Key Names

The `linkml-sqla` generator creates table names in `PascalCase` by default,
which is inconsistent with `snake_case` conventions used in SQL databases. This
can also cause issues with foreign key references, which may still point to the
`PascalCase` table names.

To fix this, we use a Python script that converts both the `__tablename__` and
any associated foreign key references from `PascalCase` to `snake_case`.

Run the script from the root of the project:

```bash
python scripts/convert_case.py
```

This will process all `.py` files in the `schemas/generated/` directory,
ensuring that all table names and foreign key references are correctly
formatted.

## 4. Integrate with Alembic

Once you have your generated and converted models, you can use Alembic to create
and apply database migrations.

### a. Configure Alembic

Ensure your `alembic/env.py` is configured to use your generated models. Each
generated SQLAlchemy model file contains its own `metadata` object. For Alembic
to be aware of these tables, you must import each metadata object and merge it
into the primary `SQLModel.metadata` that your application uses.

This ensures that when Alembic compares the current state of the database with
your models, it sees a complete picture.

```python
# alembic/env.py
import os
import sys
from pathlib import Path
from sqlmodel import SQLModel

# Add the project root to the Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import your main models
# from src.pipeline.etl.models import *

# Import metadata from your generated models
from schemas.generated.census_survey import metadata as census_metadata
from schemas.generated.geography import metadata as geography_metadata

# Combine all metadata into the main SQLModel.metadata object
# This is a crucial step for Alembic's autogenerate to detect the generated tables.
all_metadata = [census_metadata, geography_metadata]
for m in all_metadata:
    for table in m.tables.values():
        table.tometadata(SQLModel.metadata)

# Set the combined metadata as the target for Alembic
target_metadata = SQLModel.metadata
```

### b. Create a Migration

Generate a new migration file using the `alembic revision` command:

```bash
alembic revision --autogenerate -m "Add my_snake_case_name table"
```

### c. Apply the Migration

Apply the migration to your database using the `alembic upgrade` command:

```bash
alembic upgrade head
```

By following these steps, you can effectively use LinkML to define your data
models and generate SQLAlchemy models for your database, while maintaining a
clean and organized migration history with Alembic.
