import { orderResolver } from './orderResolver';

describe('orderResolver', () => {
  describe('createOrder', () => {
    it('should create an order with pickup details', () => {
      const input = {
        pickup_store_id: '123',
        pickup_time: '2023-10-27T10:00:00Z' // 10 AM
      };
      
      const result = orderResolver.Mutation.createOrder(null, { input });
      
      expect(result.pickup_store).toBe('Store-123');
      expect(result.pickup_time).toBe(input.pickup_time);
      expect(result.status).toBe('PENDING');
    });

    it('should throw error if pickup_time is missing for pickup order', () => {
      const input = {
        pickup_store_id: '123'
      };
      
      expect(() => {
        orderResolver.Mutation.createOrder(null, { input });
      }).toThrow('Pickup time is required when store pickup is selected');
    });

    it('should throw error if pickup_time is out of operating hours', () => {
      const input = {
        pickup_store_id: '123',
        pickup_time: '2023-10-27T08:00:00Z' // 8 AM
      };
      
      expect(() => {
        orderResolver.Mutation.createOrder(null, { input });
      }).toThrow('Pickup time must be within store operating hours (09:00 - 21:00)');
    });

    it('should create a regular order without pickup', () => {
      const input = {
        someOtherField: 'value'
      };
      
      const result = orderResolver.Mutation.createOrder(null, { input });
      
      expect(result.pickup_store).toBeNull();
      expect(result.pickup_time).toBeUndefined();
    });
  });
});
