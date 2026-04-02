# Road Service
This service allows users to transactionally increment, decrement, and view, the counts of lists of roadways for specific dates.  

Its three endpoints are as follows:

* > http://localhost:8001/roads/increment
* > http://localhost:8001/roads/decrement
* > http://localhost:8001/roads/counts

# Example Usage

## JSON Object Requests

Increment Request:
```json
// POST to /increment
{
  "booking_date": "2026-04-05",
  "roads": [
    { "road_id": 221, "country_code": "IE" },
    { "road_id": 333, "country_code": "UK" }
  ]
}
```

Increment Response:
```json
{
    "status":"success","booking_date":"2026-04-05",
    "roads":[
        {"road_id":221,"country_code":"IE","count":1},
        {"road_id":333,"country_code":"UK","count":1}
    ]
}
```


Decrement Request:
```json
// POST to /decrement
{
  "booking_date": "2026-04-05",
  "roads": [
    { "road_id": 221, "country_code": "IE" },
    { "road_id": 333, "country_code": "UK" }
  ]
}
```

Decrement Response:
```json
{
    "status":"success","booking_date":"2026-04-05",
    "roads":[
        {"road_id":221,"country_code":"IE","count":0},
        {"road_id":333,"country_code":"UK","count":0}
    ]
}
```


View Counts Request:
```json
// POST to /counts
{
  "booking_date": "2026-04-05",
  "roads": [
    { "road_id": 221, "country_code": "IE" },
    { "road_id": 333, "country_code": "UK" }
  ]
}
```

View Counts Response:
```json
{
    "status":"success","booking_date":"2026-04-05",
    "roads":[
        {"road_id":221,"country_code":"IE","count":0},
        {"road_id":333,"country_code":"UK","count":0}
    ]
}
```


## Example Curl Requests

Increment Request:
> curl.exe -X POST "http://localhost:8001/roads/increment" `
>   -H "Content-Type: application/json" `
>   -d "{\""booking_date\"":\""2026-04-05\"",\""roads\"":[{\""road_id\"":221, \""country_code\"":\""IE\""},{\""road_id\"":333, \""country_code\"":\""UK\""}]}"

Decrement Request:
> curl.exe -X POST "http://localhost:8001/roads/decrement" `
>   -H "Content-Type: application/json" `
>   -d "{\""booking_date\"":\""2026-04-05\"",\""roads\"":[{\""road_id\"":221, \""country_code\"":\""IE\""},{\""road_id\"":333, \""country_code\"":\""UK\""}]}"


View Counts Request:
> curl.exe -X POST "http://localhost:8001/roads/counts" `   
>   -H "Content-Type: application/json" `
>   -d "{\""booking_date\"":\""2026-04-05\"",\""roads\"":[{\""road_id\"":221, \""country_code\"":\""IE\""},{\""road_id\"":333, \""country_code\"":\""UK\""}]}"
