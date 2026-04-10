# user-srv

User service providing user registration and authentication. Issues Json Web Tokens to maintain login status.

## API

### `POST /register`

Registers a new user. Accepts username and password.
```sh
curl http://localhost:8003/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test123", "password": "password"}'

{"id": "b586b350-0ea1-4044-8924-c9c55bb406cb"}
```


### `POST /login`

Authenticates a user using username and password and returns a JWT.
This JWT should then be used with Authorization header as a Bearer token for calls to other services.
```sh
curl http://localhost:8003/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test123", "password": "password"}'

{
  "id": "b586b350-0ea1-4044-8924-c9c55bb406cb",
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### `DELETE /users/me`
Deletes the currently authenticated user (based on supplied bearer token)
```sh
curl -X DELETE http://localhost:8003/users/me \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

{
  "detail": "User deleted successfully"
}
```

### `GET /public_key`
Returns the public key that can be used to verify JWT signatures. Intended to be queried by other services
```sh
curl http://localhost:8003/public_key

{
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
}
```

### `GET /validate`
Validates a JWT. Not intended for inter-service validation (use `/public_key` instead)
```sh
curl http://localhost:8003/validate \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

{
  "status": "ok"
}
```

## Private key for signing

To get a private key `app/private.pem` for signing JWTs generated you can run the following command:
```sh
docker run --rm alpine/openssl genrsa 2048 > app/private.pem
```
To avoid setup issues a sample private key is checked in.


