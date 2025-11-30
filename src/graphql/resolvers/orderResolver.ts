import { validateOrderInput } from './orderInputResolver';

export const orderResolver = {
  Query: {
    order: (_, { id }) => {
      // fetch order
      return { id, total: 100 };
    }
  },
  Mutation: {
    createOrder: (_, { input }) => {
      // Validate input including pickup logic
      validateOrderInput(input);
      
      // create order logic
      return { 
        id: "123", 
        ...input, 
        total: 100, 
        status: "PENDING", 
        createdAt: new Date().toISOString(),
        // Map input fields to schema fields
        pickup_store: input.pickup_store_id ? `Store-${input.pickup_store_id}` : null,
        pickup_time: input.pickup_time
      };
    }
  }
};

