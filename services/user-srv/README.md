### user-srv

This service exposes two endpoints:

- `POST /register` to register a user. It accepts `username` and `password` parameters.

```shell
curl http://localhost:8003/register -H "Content-Type: application/json" -d '{"username": "hello@email.com", "password": "password"}'

{"id": "b586b350-0ea1-4044-8924-c9c55bb406cb"}
```

- `POST /login` logs a user in. It takes the same parameters as `POST /register` and returns a user alongside a token.

```shell
curl http://localhost:8003/login -H "Content-Type: application/json" -d '{"username": "hello@email.com", "password": "password"}'

{
	"id": "b586b350-0ea1-4044-8924-c9c55bb406cb",
	"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZDdlOWEwZS0yZmUxLTRhZGItYTdmZi05YzdmZDc5MDQyYzAiLCJ1c2VybmFtZSI6ImhlbGxvQGVtYWlsLmNvbSIsImV4cCI6MTc3NTc5NTU5NX0.dep498yzuiMvbYemoSq8kQle2RehnJfBg69fsB4aJF0",
	"username": "hello@email.com",
}
```
