# Lightwallet API
This document describes a reference standard specification for the Monero
lightwallet server/client API. It’s implemented by OpenMonero, MyMonero, and
the official Monero project, and is maintained with the purpose of organizing
and recording the consensus of Monero lightwallet API projects, and to support
alternate implementations.

Modifications to this specification should only be made with consensus of the
projects which participate by implementing the specification.

## Encoding Schemes
### JSON
JSON is the original and required encoding scheme used for the API. Binary
values (public keys, hashes, etc) are sent as an ascii-hex string. Some
integers, that may exceed 2^53, are sent as strings. This is to due to the
limitation within Javascript where all integers are double floating point
values.

## Transport Layers
### HTTP-REST
When calling an API method, the client must use HTTP POST to a path with the
method name. As an example, to invoke the `get_address_txs` method, the client
sends a POST message to `/get_address_txs` where the body contains the JSON
request object associated with that method name. If the requested method does
not exist, a HTTP 404 "Not Found" error must be returned. If the request type
is not POST, the server shall return a HTTP 405 "Method Not Allowed" error. If
the server is unable to complete a request temporarily due to load, then the
server shall return a HTTP 503 "Service Unavailable" error to indicate to the
client that the request may be serviceable later.

Servers must support the JSON encoding scheme. The client must send the HTTP
field `Content-Type: application/json`; if the server is not provided that
content type from the client then the server shall respond with a HTTP 415
"Unsupported Media Type" error.

This transport layer does not use HTTP authentication, and instead uses the
`view_key` field for authorization. Documentation for a specific method will
indicate whether `view_key` is required. When it is not necessary, anyone can
invoke the method.

## Schema
The ascii name of the field is used as a key in JSON encoding. If a field has
a `*` indicator, that means the field is optional. If `*` is used next to the
type, the value can be "null" or a value valid according to the type.

### Types
**binary**

A hex-ascii string in JSON. This is generally some irreducible cryptographic
concept - a public key or hash.

**base58-address**

A Monero public address encoded as a string in JSON.

**address_meta** object

|     Field     |       Type       |       Description      |
|---------------|------------------|------------------------|
| `address`     | `base58-address` | Monero public address  |
| `major_index` | `uint32`         | Subaddress major index |
| `minor_index` | `uint32`         | Subaddress minor index |

**output** object

Information needed to spend an output.

|       Field      |           Type            |          Description          |
|------------------|---------------------------|-------------------------------|
| tx_id            | `uint64`                  | Index of tx in blockchain     |
| amount           | `uint64-string`           | XMR value of output           |
| index            | `uint16`                  | Index within vout vector      |
| global_index     | `uint64-string`           | Index within amount           |
| rct              | `binary`                  | Bytes of ringct data          |
| tx_hash          | `binary`                  | Bytes of tx hash              |
| tx_prefix_hash   | `binary`                  | Bytes of tx prefix hash       |
| public_key       | `binary`                  | Bytes of output public key    |
| tx_pub_key       | `binary`                  | Bytes of the tx public key    |
| spend_key_images | array of `binary` objects | Bytes of key images           |
| timestamp        | `timestamp`               | Timestamp of containing block |
| height           | `uint64`                  | Containing block height       |
| recipient        | `address_meta` object     | Address data of the recipient |

> `tx_id` is determined by the monero daemon. It is the offset that a
> transaction appears in the blockchain from the genesis block.

> `global_index` is determined by the monero daemon. It is the offset from the
> first time the amount appeared in the blockchain. After ringct, this is the
> order of outputs as they appear in the blockchain.

> `tx_hash` and `tx_prefix_hash` are determined by how `monerod` computes the
> hash.

> `rct` is, for ringct outputs, a 96-byte blob containing the concatenation
> of the public commitment, then the ringct mask value, and finally the
> ringct amount value. For ringct coinbase outputs, the mask is always the
> identity mask and the amount is zero; for non-coinbase ringct outputs, the
> mask and amount are the respective raw encrypted values, which must be
> decrypted by the client using the view secret key. For non-ringct outputs,
> this field is nil.

**rates** object

| Field |   Type    |      Description      |
|-------|-----------|-----------------------|
| AUD * | `float32` | AUD/XMR exchange rate |
| BRL * | `float32` | BRL/XMR exchange rate |
| BTC * | `float32` | BTC/XMR exchange rate |
| CAD * | `float32` | CAD/XMR exchange rate |
| CHF * | `float32` | CHF/XMR exchange rate |
| CNY * | `float32` | CNY/XMR exchange rate |
| EUR * | `float32` | EUR/XMR exchange rate |
| GBP * | `float32` | GBP/XMR exchange rate |
| HKD * | `float32` | HKD/XMR exchange rate |
| INR * | `float32` | INR/XMR exchange rate |
| JPY * | `float32` | JPY/XMR exchange rate |
| KRW * | `float32` | KRW/XMR exhcnage rate |
| MXN * | `float32` | MXN/XMR exchange rate |
| NOK * | `float32` | NOK/XMR exchange rate |
| NZD * | `float32` | NZD/XMR exchange rate |
| SEK * | `float32` | SEK/XMR exchange rate |
| SGD * | `float32` | SGD/XMR exchange rate |
| TRY * | `float32` | TRY/XMR exchange rate |
| USD * | `float32` | USD/XMR exchange rate |
| RUB * | `float32` | RUB/XMR exchange rate |
| ZAR * | `float32` | ZAR/XMR exchange rate |

> If an exchange rate is unavailable, the server field shall omit the field
> from the JSON object.

**spend** object

|    Field   |          Type         |        Description         |
|------------|-----------------------|----------------------------|
| amount     | `uint64-string`       | XMR possibly being spent   |
| key_image  | `binary`              | Bytes of the key image     |
| tx_pub_key | `binary`              | Bytes of the tx public key |
| out_index  | `uint16`              | Index of source output     |
| mixin      | `uint32`              | Mixin of the spend         |
| sender     | `address_meta` object | Address data of the sender |

> `out_index` is a zero-based offset from the original received output. The
> variable within the monero codebase is the `vout` array, this is the index
> within that. It is needed for correct computation of the `key_image`.

> `mixin` does not include the real spend - this is the number of dummy inputs.

**timestamp**

A string in JSON. The string format is "YYYY-HH-MM-SS.0-00:00". Monero
blockchain timestamps do not have sub-seconds.

**transaction** object

|     Field      |           Type           |        Description        |
|----------------|--------------------------|---------------------------|
| id             | `uint64`                 | Index of tx in blockchain |
| hash           | `binary`                 | Bytes of tx hash          |
| timestamp *    | `timestamp`              | Timestamp of block        |
| total_received | `uint64-string`          | Total XMR received        |
| total_sent     | `uint64-string`          | XMR possibly being spent  |
| unlock_time    | `uint64`                 | Tx unlock time field      |
| height *       | `uint64`                 | Block height              |
| spent_outputs  | array of `spend` objects | List of possible spends   |
| payment_id *   | `binary`                 | Bytes of tx payment id    |
| coinbase       | `boolean`                | True if tx is coinbase    |
| mempool        | `boolean`                | True if tx is in mempool  |
| mixin          | `uint32`                 | Mixin of the receive      |

> `id` is determined by the monero daemon. It is the offset that a
> transaction appears in the blockchain from the genesis block.

> `timestamp` and `height` are not sent when `mempool` is true.

> `hash` is determined by how the monero core computes the hash.

> `spent_outputs` is the list of possible spends in _this_ transaction only.

> `payment_id` is omitted if the transaction had none. It is decrypted when the
> encrypted form is used. The decryption may be incorrect - if the transaction
> was TO another address, then this will be random bytes. This happens
> frequently with outgoing payment ids; the received XMR in the transaction is
> change and the payment id is for the real recipient.

> `mixin` does not include the real spend - this is the number of dummy inputs.

**uint16** / **uint32** / **uint64**

Sent as a standard decimal encoded number in JSON. The JSON decoder must reject
number values that exceed the specified bit-width.

**uint64-string**

A uint64 encoded as a decimal string value in JSON. Used when a value may
exceed 2^53 - all numbers are 64-bit floats in JavaScript.

**random_output** object

|     Field    |       Type      |            Description             |
|--------------|-----------------|------------------------------------|
| global_index | `uint64-string` | Index within amount                |
| public_key   | `bytes`         | Bytes of output public key         |
| rct          | `bytes`         | Bytes containing ringct commitment |

> `global_index` is determined by the monero daemon. It is the offset from the
> first time the amount appeared in the blockchain. After ringct, this is the
> order of outputs as they appear in the blockchain.

**random_outputs** object

Randomly selected outputs for use in a ring signature.

|   Field   |               Type               |       Description       |
|-----------|----------------------------------|-------------------------|
|  amount   | `uint64-string`                  | XMR amount, 0 if ringct |
| outputs * | array of `random_output` objects | Selected outputs        |

> `outputs` is omitted by the server if the `amount` does not have enough
> mixable outputs.

### Methods
#### `get_address_info`
Returns the minimal set of information needed to calculate a wallet balance,
including the balance of subaddresses. The server cannot calculate when a spend
occurs without the spend key, so a list of candidate spends is returned.

**Request** object

|   Field   |       Type       |            Description                |
|-----------|------------------|---------------------------------------|
| address   | `base58-address` | Standard address of the wallet        |
| view_key  | `binary`         | View key bytes for authorization      |

> If `address` is not authorized, the server must return a HTTP 403
> "Forbidden" error.

> If `address` is not a standard address, the server must return a HTTP 400
> "Bad Request" error.

**Response** object

|        Field         |          Type            |       Description         |
|----------------------|--------------------------|---------------------------|
| locked_funds         | `uint64-string`          | Sum of unspendable XMR    |
| total_received       | `uint64-string`          | Sum of received XMR       |
| total_sent           | `uint64-string`          | Sum of possibly spent XMR |
| scanned_height       | `uint64`                 | Current tx scan progress  |
| scanned_block_height | `uint64`                 | Current scan progress     |
| start_height         | `uint64`                 | Start height of response  |
| transaction_height   | `uint64`                 | Total txes sent in Monero |
| blockchain_height    | `uint64`                 | Current blockchain height |
| spent_outputs        | array of `spend` objects | Possible spend info       |
| rates *              | `rates`                  | Current exchange rates    |

> `rates` is omitted if unavailable.

#### `get_address_txs`
Returns information needed to show transaction history. The server cannot
calculate when a spend occurs without the spend key, so a list of candidate
spends is returned. The response should show a wallet's entire history,
including transactions to and from subaddresses.

**Request** object

|   Field  |        Type      |             Description               |
|----------|------------------|---------------------------------------|
| address  | `base58-address` | Standard address of the wallet        |
| view_key | `binary`         | View key bytes for authorization      |

> If `address` is not authorized, the server must return a HTTP 403
> "Forbidden" error.

> If `address` is not a standard address, the server must return a HTTP 400
> "Bad Request" error.

**Response** object

|        Field         |             Type               |       Description         |
|----------------------|--------------------------------|---------------------------|
| total_received       | `uint64-string`                | Sum of received outputs   |
| scanned_height       | `uint64`                       | Current tx scan progress  |
| scanned_block_height | `uint64`                       | Current scan progress     |
| start_height         | `uint64`                       | Start height of response  |
| blockchain_height    | `uint64`                       | Current blockchain height |
| transactions         | array of `transaction` objects | Possible spend info       |

#### `get_random_outs`
Selects random outputs to use in a ring signature of a new transaction. If the
`amount` is `0` then the `monerod` RPC `get_output_distribution` should be used
to locally select outputs using a gamma distribution as described in "An
Empirical Analysis of Traceability in the Monero Blockchain". If the `amount`
is not `0`, then the `monerod` RPC `get_output_histogram` should be used to
locally select outputs using a triangular distribution
(`uint64_t dummy_out = histogram.total * sqrt(float64(random_uint53) / float64(2^53))`).

**Request** object

|    Field   |               Type               |          Description             |
|------------|----------------------------------|----------------------------------|
| count      | `uint32`                         | Mixin (name is historical)       |
| amounts    | array of `uint64-string` objects | XMR amounts that need mixing     |

> Clients must use amount `0` when computing a ringct output.

> If clients are creating multiple rings with the same amount, they must set
> `count` to the mixin level and add the value to `amounts` multiple times.
> Server must respond to each value in `amounts`, even if the value appears
> multiple times.

**Response** object

|    Field    |               Type               |          Description             |
|-------------|----------------------------------|----------------------------------|
| amount_outs | array of `random_output` objects | Dummy outputs for each `amounts` |

> If there are not enough outputs to mix for a specific amount, the server
> shall omit the `outputs` field in `amount_outs`.

#### `get_unspent_outs`
Returns a list of received outputs to the wallet, including to subaddresses.
The client must determine when the output was actually spent.

**Request** object

|       Field      |       Type       |           Description            |
|------------------|------------------|----------------------------------|
| address          | `base58-address` | Standard address of the wallet   |
| view_key         | `binary`         | View key bytes                   |
| amount           | `uint64-string`  | XMR send amount                  |
| mixin            | `uint32`         | Minimum mixin for source output  |
| use_dust         | `boolean`        | Return all available outputs     |
| dust_threshold * | `uint64-string`  | Ignore outputs below this amount |

> If the total received outputs for the address is less than `amount`, the
> server shall return a HTTP 400 "Bad Request" error code.

> If `address` is not a standard address, the server must return a HTTP 400
> "Bad Request" error.

**Response** object

|    Field     |           Type            |                Description              |
|--------------|---------------------------|-----------------------------------------|
| per_byte_fee | `uint64-string`           | Estimated network fee                   |
| fee_mask     | `uint64-string`           | Fee quantization mask                   |
| amount       | `uint64-string`           | The total value in outputs              |
| outputs      | array of `output` objects | Outputs possibly available for spending |

#### `import_request`
Request an account scan from the genesis block.

**Request** object

|   Field  |       Type       |            Description         |
|----------|------------------|--------------------------------|
| address  | `base58-address` | Standard address of the wallet |
| view_key | `binary`         | View key bytes                 |

**Response** object

|       Field        |       Type       |           Description            |
|--------------------|------------------|----------------------------------|
| payment_address *  | `base58-address` | Payment location                 |
| payment_id *       | `binary`         | Bytes for payment_id tx field    |
| import_fee *       | `uint64-string`  | Fee required to complete request |
| new_request        | `boolean`        | New or existing request          |
| request_fulfilled  | `boolean`        | Indicates success                |
| status             | `string`         | Custom message                   |

> `payment_id`, `import_fee`, and `payment_address` may be omitted if the
> client does not need to send XMR to complete the request.

> If `address` is not a standard address, the server must return a HTTP 400
> "Bad Request" error.

#### `login`
Check for the existence of an account or create a new one.

**Request** object

|       Field       |       Type       |           Description            |
|-------------------|------------------|----------------------------------|
| address           | `base58-address` | Standard address of the wallet   |
| view_key          | `binary`         | View key bytes                   |
| create_account    | `boolean`        | Try to create new account        |
| generated_locally | `boolean`        | Indicate that the address is new |

> The view key bytes are required even if an account is not being created, to
> prevent metadata leakage.

> If the server does not allow account creations, HTTP 501 "Not Implemented"
> error must be returned.

> If approval process is manual, a successful HTTP 200 OK and response object
> must be returned. Subsequent requests shall be HTTP 403 "Forbidden" until
> account is approved.

> If `address` is not a standard address, the server must return a HTTP 400
> "Bad Request" error.

**Response** object

|        Field        |   Type    |            Description             |
|---------------------|-----------|------------------------------------|
| new_address         | `boolean` | Whether account was just created   |
| generated_locally * | `boolean` | Flag from initial account creation |
| start_height *      | `uint64`  | Account scanning start block       |

#### `submit_raw_tx`
Submit raw transaction to be relayed to monero network.

**Request** object

| Field |   Type   |                     Description                           |
|-------|----------|-----------------------------------------------------------|
| tx    | `binary` | Raw transaction bytes, in format used by daemon p2p comms |

> This format is tricky unfortunately, it is custom to the monero daemon. The
> internal code of `monerod` must be read to determine this format currently.

**Response** object

| Field  |   Type   |   Description   |
|--------|----------|-----------------|
| status | `string` | Status of relay |

> `status` is typically the response by the monero daemon attempting to relay
> the transaction.
