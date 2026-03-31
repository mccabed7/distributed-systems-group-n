# Road Service
This service allows users to transactionally increment, decrement, and view, the counts of lists of roadways for specific dates.  

Its three endpoints [/increment, /decrement, /counts] can be accessed at http://localhost:8001/roads/.

# Example Usage

Increment Request:

>> curl.exe -X POST "http://localhost:8001/roads/increment" `
>>   -H "Content-Type: application/json" `
>>   -d "{\""country_code\"":\""IE\"",\""booking_date\"":\""2026-04-05\"",\""road_ids\"":[101,102,103]}"

Increment Response:
>> {"country_code":"IE","booking_date":"2026-04-05","counts":{"101":2,"102":2,"103":2}}


Decrement Request:
>> curl.exe -X POST "http://localhost:8001/roads/decrement" `
>>   -H "Content-Type: application/json" `
>>   -d "{\""country_code\"":\""IE\"",\""booking_date\"":\""2026-04-05\"",\""road_ids\"":[102,103]}" 

Decrement Response:
>> {"country_code":"IE","booking_date":"2026-04-05","counts":{"102":1,"103":1}}


View Counts Request:
>> curl.exe -X POST "http://localhost:8001/roads/counts" `   
>>   -H "Content-Type: application/json" `
>>   -d "{\""country_code\"":\""IE\"",\""booking_date\"":\""2026-04-05\"",\""road_ids\"":[101,102,103]}"

View Counts Response:
>> {"country_code":"IE","booking_date":"2026-04-05","counts":{"101":3,"102":2,"103":2}}