// Helper for input validation
export const validateOrderInput = (input: any) => {
  if (!input.items || input.items.length === 0) {
    throw new Error("Order must have items");
  }
  
  if (input.pickup_store_id) {
    if (!input.pickup_time) {
      throw new Error("Pickup time is required when selecting a store");
    }
    
    // Ensure pickup_time is within store operating hours (e.g. 9am - 9pm)
    const pickupDate = new Date(input.pickup_time);
    const hour = pickupDate.getHours();
    if (hour < 9 || hour >= 21) {
      throw new Error("Pickup time must be within store operating hours (9am - 9pm)");
    }
  }
  
  return true;
};

