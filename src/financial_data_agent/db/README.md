# PostGreSQL Database

### Start database
Run database locally in Docker container
```bash
docker compose up -d
```

### Create table
```bash
createdb -U postgres -h localhost financial_data_agent
```

### Migrations
Create and apply migration
```bash
alembic revision --autogenerate -m "migration name"
alembic upgrade head
```