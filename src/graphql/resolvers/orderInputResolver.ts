export const validateOrderInput = (input: any) => {
  if (input.pickup_store_id) {
    if (!input.pickup_time) {
      throw new Error("Pickup time is required when store pickup is selected");
    }

    const pickupDate = new Date(input.pickup_time);
    if (isNaN(pickupDate.getTime())) {
        throw new Error("Invalid pickup time format");
    }

    const hour = pickupDate.getHours();
    // Store hours: 9 AM to 9 PM (21:00)
    if (hour < 9 || hour >= 21) {
      throw new Error("Pickup time must be within store operating hours (09:00 - 21:00)");
    }
  }
};
