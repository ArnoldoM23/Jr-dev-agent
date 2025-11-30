import { orderResolver } from './orderResolver';

// Mock test runner (since we don't have a full TS environment here)
console.log("Running tests...");

const runTests = () => {
  try {
    // Test 1: Pickup order within hours
    const input = {
      items: [{ id: 1 }],
      paymentMethod: "CREDIT",
      pickup_store_id: "123",
      pickup_time: "2023-10-27T10:00:00Z" // 10am UTC
    };
    // Note: simplified test, ignoring timezone issues for mock
    const result = orderResolver.Mutation.createOrder(null, { input });
    
    if (result.pickup_store === "Store-123") {
      console.log("Test 1 Passed: Pickup store set correctly");
    } else {
      console.error("Test 1 Failed");
    }

    // Test 2: Pickup order out of hours
    try {
      const badInput = {
        items: [{ id: 1 }],
        paymentMethod: "CREDIT",
        pickup_store_id: "123",
        pickup_time: "2023-10-27T23:00:00Z" // 11pm UTC
      };
      // We might need to adjust logic if the resolver uses local time
      // For this mock, let's assume the resolver logic holds.
      orderResolver.Mutation.createOrder(null, { input: badInput });
      console.error("Test 2 Failed: Should have thrown error");
    } catch (e: any) {
      if (e.message.includes("operating hours")) {
        console.log("Test 2 Passed: Operating hours validation working");
      } else {
          console.error("Test 2 Failed: Wrong error message: " + e.message);
      }
    }

  } catch (e) {
    console.error("Tests failed", e);
  }
};

runTests();

