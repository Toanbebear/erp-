# AUTHENTICATION 

- login 
- logout

In order to be able to access any document an access token needs to generated which serves as 
session cookies in a regular web language. The token will **be needed** for every subsequent requests.
Except for */api/auth/token* enpoint that accept **multipart/form-data** as the Content type every other 
endpoints accept application/json as the 'Content Type'

# REQUEST ACCESS TOKEN

```bash
curl --request GET 
  --url http://192.168.43.58:8069/api/auth/token 
  --form db=api.ng 
  --form login=admin 
  --form password=admin
```

Python request


```python
import requests

url = "http://192.168.43.58:8069/api/auth/token"

payload = {
  "db":"api.ng", 
  "login": "admin", 
  "password": "admin"
}

headers = {
    'content-type': "multipart/form-data; 
    'access-token': "access_token_ebb1914bbdb5622cd782a1a0ff51f81a2cba042a"
    }

response = requests.request("GET", url, data=payload, headers=headers)

print(response.text)
```
To retrive an access token these following parameters needs to be set.

* the database name as **db**
* the connecting username as **login**
* the user password as **password**
The above request will return a response like below.

```python
{
  "uid": 2,
  "user_context": {
    "lang": "en_US",
    "tz": "Europe/Brussels",
    "uid": 2
  },
  "company_id": 1,
  "company_ids": [
    1
  ],
  "partner_id": 3,
  "access_token": "access_token_ebb1914bbdb5622cd782a1a0ff51f81a2cba042a",
  "expires_in": "31536000"
}
```
The most interesting part of the response is the access token field, *access_token_ebb1914bbdb5622cd782a1a0ff51f81a2cba042a* for every other request the token should to be send along the request headers else an invalid token response will be generated.

# LOGOUT

To logout of the system the token needs to be destroyed i.e deleted, by doing that the user/application making the request on behalf of the user  will have not futher access to Odoo.
The token */api/auth/token* listen to both **GET** and **DELETE** requests, GET will fetch the token while delete request will deleted the token.

```python
import requests

url = "http://192.168.43.58:8069/api/auth/token"

payload = {
  "db":"api.ng", 
  "login": "admin", 
  "password": "admin"
}

headers = {
    'content-type': "multipart/form-data; 
    'access-token': "access_token_ebb1914bbdb5622cd782a1a0ff51f81a2cba042a"
    }

response = requests.request("DELETE", url, data=payload, headers=headers)

print(response.text)
```
# SALE

To get or fetch existing sale order
```python
import requests

url = "http://192.168.43.58:8069/api/sale.order"

payload = "{
   "limit": 2, 
   "fields": "['id', 'partner_id', 'name']", 
   "domain":"[('id', 'in', [10,11,12,13,14])]", 
   "offset":0
  }"

headers = {
    'access-token': "access_token_79406d541ea0a79a942e19871a9c806236d5638c",
    'content-type': "application/json"
    }

response = requests.request("GET", url, data=payload, headers=headers)

print(response.text)
```
There is posibilty of applying some record filters in order to get just the specific record.
* limit: This define the total number of record we are expecting
* offset: where the query will start from
* fields: this is the list of field that we wanted to return, this can be leave empty if we wanted to return all the fields.
* domain: domain is like a filter it is always a list of tuples *(field, operator, value)*


These payload applies to all records in Odoo.


We can perform create, update and delete operation on any records using corresponding HTTP request headers.

**GET**: For  retriving existing records
**POST**: For creating new records
**PATCH**: Call an action button on a record
**DELETE**: To delete a record

All the API of currently installed modules or any module that may be installed has already cattered for dynamically. 
The API follows this sematic pattern

**/api{api route}/modelP{model name}/id{optional id for delete request}**
e.g for sale order 
Get request to **api/sale.order** endpoint will return all the sale order in the system.


# Sale Order
* GET Request
```python
import requests

url = "http://192.168.43.58:8069/api/sale.order"

payload = "{}"
headers = {
    'content-type': "application/json"
    }

response = requests.request("GET", url, data=payload, headers=headers)

print(response.text)
```
* Response
```python
{
  "count": 1,
  "data": [
    {
      "id": 30,
      "name": "SO029",
      "origin": false,
      "client_order_ref": false,
      "reference": false,
      "state": "draft",
      "date_order": "2020-06-30T20:58:48.269652",
      "validity_date": false,
      "require_signature": true,
      "require_payment": true,
      "create_date": "2020-06-30T20:58:39.806639",
      "confirmation_date": false,
      "user_id": [
        6,
        "Marc Demo"
      ],
      "partner_id": [
        11,
        "Gemini Furniture"
      ],
      "partner_invoice_id": [
        31,
        "Gemini Furniture, Oscar Morgan"
      ],
      "partner_shipping_id": [
        31,
        "Gemini Furniture, Oscar Morgan"
      ],
      "pricelist_id": [
        1,
        "Public Pricelist (USD)"
      ],
      "analytic_account_id": false,
      "order_line": [
        55
      ],
      "invoice_status": "no",
      "note": "",
      "amount_untaxed": 33.0,
      "amount_tax": 0.0,
      "amount_total": 33.0,
      "currency_rate": 1.5289,
      "payment_term_id": false,
      "fiscal_position_id": false,
      "company_id": [
        1,
        "YourCompany"
      ],
      "team_id": [
        2,
        "Website"
      ],
      "signature": false,
      "signed_by": false,
      "commitment_date": false,
      "transaction_ids": [],
      "cart_recovery_email_sent": false,
      "website_id": false,
      "campaign_id": false,
      "source_id": false,
      "medium_id": false,
      "activity_ids": [],
      "message_follower_ids": [
        167,
        168
      ],
      "message_ids": [
        218,
        217
      ],
      "message_main_attachment_id": false,
      "website_message_ids": [],
      "access_token": false,
      "create_uid": [
        1,
        "OdooBot"
      ],
      "write_uid": [
        1,
        "OdooBot"
      ],
      "write_date": "2020-06-30T20:58:39.806639",
      "is_expired": false,
      "remaining_validity_days": 0,
      "currency_id": [
        2,
        "USD"
      ],
      "invoice_count": 0,
      "invoice_ids": [],
      "amount_by_group": [],
      "expected_date": "2020-07-03T06:54:53",
      "amount_undiscounted": 33.0,
      "type_name": "Quotation",
      "authorized_transaction_ids": [],
      "website_order_line": [
        55
      ],
      "cart_quantity": 2,
      "only_services": false,
      "is_abandoned_cart": true,
      "activity_state": false,
      "activity_user_id": false,
      "activity_type_id": false,
      "activity_date_deadline": false,
      "activity_summary": false,
      "message_is_follower": false,
      "message_partner_ids": [
        2,
        7
      ],
      "message_channel_ids": [],
      "message_unread": false,
      "message_unread_counter": 0,
      "message_needaction": false,
      "message_needaction_counter": 0,
      "message_has_error": false,
      "message_has_error_counter": 0,
      "message_attachment_count": 0,
      "access_url": "/my/orders/30",
      "access_warning": "",
      "display_name": "SO029",
      "__last_update": "2020-06-30T20:58:39.806639"
    }
  ]
}
```
The reponse with all the fields, but the return fields can specified along side the request, and also, specific records can be specified by sending along the request Odoo domain as json body.
```python
{"limit": 2, "fields": "['id', 'partner_id', 'name']", "domain":"[('id', 'in', [10,11,12,13,14])]", "offset":0}
```
The above will only return **2** maximum records, id, partner and sale order name, that have an ID in the given list [10,11,12,13,14], the offset can be set also.

* POST (Create Sale Order)
```python
import requests

url = "http://192.168.43.58:8069/api/sale.order"

payload = {'partner_id': 10, '__api__order_line':[(0, 0,  {'product_id': 1,'price_unit':4000})]"}
headers = {
    'content-type': "application/json",
    'access-token': "access_token_79406d541ea0a79a942e19871a9c806236d5638c"
    }

response = requests.request("POST", url, data=payload, headers=headers)

print(response.text)

```
Note the **__api__**order_line the bolded part.
The \__api\__ is a shortcut (instead of created the line item separately from the main record), it is a way of telling the system that an order line or line Items is being created from an api endpoint. 
**order_line** is the One2many field that line sale order and order line together.

> This pattern is applicable to other models


* PATCH REQUEST
Path request is meant for calling an action button on a record. e.g validating sale order.

```python
import requests

url = "http://192.168.43.58:8069/api/sale.order/37"

payload = {"_method":"action_confirm"}
headers = {
    'content-type': "application/json",
    'access-token': "access_token_79406d541ea0a79a942e19871a9c806236d5638c"
    }

response = requests.request("PATCH", url, data=payload, headers=headers)

print(response.text)
```
In the above request, we send a json body like this **{"_method":"action_confirm"}** The **_method** is the action/button name in odoo. This is similar to clicking *Confirm* Button on sale order with ID **37**

* DELETE SALE ORDER
```python
import requests

url = "http://192.168.43.58:8069/api/sale.order/37"

payload = "{}"
headers = {
    'content-type': "application/json",
    'access-token': "access_token_79406d541ea0a79a942e19871a9c806236d5638c"
    }

response = requests.request("DELETE", url, data=payload, headers=headers)

print(response.text)
```
We only need to make a delete request to the resource.

# Danh sách key trong redis
    