# science_logic_pwr
Graphql query to Fetch all devices.

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