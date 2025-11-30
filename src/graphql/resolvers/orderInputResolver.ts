type OrderInput = {
  pickup_store_id?: string;
  pickup_time?: string;
  [key: string]: unknown;
};

type PickupStore = {
  id: string;
  name: string;
  openHour: number;
  closeHour: number;
};

const OPERATING_HOURS_MESSAGE =
  'Pickup time must be within store operating hours (09:00 - 21:00)';

const PICKUP_STORES: Record<string, PickupStore> = {
  '123': { id: '123', name: 'Store-123', openHour: 9, closeHour: 21 },
  '456': { id: '456', name: 'Store-456', openHour: 9, closeHour: 21 },
  '789': { id: '789', name: 'Store-789', openHour: 9, closeHour: 21 }
};

export const getPickupStoreMetadata = (storeId?: string): PickupStore | null => {
  if (!storeId) {
    return null;
  }

  return PICKUP_STORES[storeId] ?? null;
};

const parsePickupDate = (value: string): Date => {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new Error('Pickup time must be a valid ISO-8601 date');
  }

  return date;
};

export const validateOrderInput = (input: OrderInput) => {
  const wantsPickup = Boolean(input.pickup_store_id || input.pickup_time);

  if (!wantsPickup) {
    return;
  }

  if (!input.pickup_store_id) {
    throw new Error('Pickup store ID is required when store pickup is selected');
  }

  const store = getPickupStoreMetadata(input.pickup_store_id);
  if (!store) {
    throw new Error('Selected store is not available for pickup');
  }

  if (!input.pickup_time) {
    throw new Error('Pickup time is required when store pickup is selected');
  }

  const pickupDate = parsePickupDate(input.pickup_time);
  const hour = pickupDate.getUTCHours(); // Assuming UTC for simplicity

  if (hour < store.openHour || hour >= store.closeHour) {
    throw new Error(OPERATING_HOURS_MESSAGE);
  }
};
