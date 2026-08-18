# PostGreSQL Database

### Start Postgres
Run database locally in Docker container
```bash
docker compose up -d
```

Verify it is running
```bash
docker compose ps -a
```

### Stop Postgres
```bash
docker compose down
```

### Migrations
Create and apply migration
```bash
alembic revision --autogenerate -m "migration name"
alembic upgrade head
```