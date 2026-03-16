# science_logic_pwr
1. Graphql query to Fetch all devices.
2. This is a significant upgrade. We are moving from multiple, heavy REST API calls (which required calculating counts from a database first) to a single, efficient GraphQL query.
3. Instead of two separate REST calls, we get the name, ip, and deviceClass in one response.
4. It uses the hasNextPage and cursor logic to ensure 100% data coverage.
5. We no longer need to query the SQL database for a count, as GraphQL handles the limits.


# QUERY LOGICAL FLOW:

### URL Manipulation:
 I added .replace('/api', '/gql'). Most ScienceLogic/SL1 platforms host the GraphQL endpoint at /gql. Please verify if your endpoint matches this.

### The Loop: 
 The while has_next_page: loop is the engine. It starts with an empty cursor, gets 500 records, finds the cursor for the last item, and feeds it back in until the database is empty.

### Efficiency: 
Instead of doing string splits on URIs manually for classes and info separately, the GQL query returns the deviceClass object nested inside the device node. We process everything in one loop over the all_devices list.

# Device Inventory GraphQL Integration Guide
Overview
This document outlines the standard procedure for fetching device data from the API. The API uses the Relay Connection Specification, which employs cursor-based pagination to manage large datasets efficiently.

## The "Full Fetch" Query
To retrieve the complete list of devices, use the following query. By setting the first argument to a high number (e.g., 500), you can often capture the entire database in a single request if the total count is below that threshold.

''''
query GetFullDeviceInventory($batchSize: Int = 500, $cursor: String = "") {
  devices(first: $batchSize, after: $cursor) {
    pageInfo {
      hasNextPage    # Boolean: True if more records exist
      matchCount     # Integer: Total records in the database
      __typename
    }
    edges {
      cursor         # The unique "bookmark" for this specific record
      node {
        id
        name
        ip
        deviceClass {
          class
          description
        }
      }
    }
  }
}
''''

## 1. The Pagination Pattern (Edges & Nodes)
Unlike simple REST arrays, this API wraps data in edges.

Node: The actual device data (ID, IP, Name).

Edge: A wrapper that includes the node and a cursor.

Cursor: A Base64 encoded string representing the position of that item in the database.

## 2. Argument Requirements
The devices field requires two specific arguments to function correctly:

first (Int): Limits the number of results. If omitted, the server defaults to 10.

after (String): Tells the server where to start looking. For the first page, use an empty string ("").

## 3. Understanding matchCount vs. Result Set
matchCount represents the total number of devices available in the DB (e.g., 394).

If your first value is greater than the matchCount, you will receive all devices at once, and hasNextPage will be false.

If your first value is smaller than the matchCount, you must perform multiple requests (Pagination).