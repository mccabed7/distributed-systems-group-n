### user-srv

This service exposes one endpoint:

- `POST /register` to register a user. It accepts `username` and `password` parameters.

```shell
curl http://localhost:8003/register -H "Content-Type: application/json" -d '{"username": "hello@email.com", "password": "password"}'
```
