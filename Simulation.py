##-- Import Classes --##
from Hospital import Hospital
from Wholesaler import Wholesaler
from Manufacturer import Manufacturer


##-- Class --##
class Simulation():

    ## Initialization
    def __init__(self, sim_periods, hospitals, wholesalers, manufacturers, disruption_function, change_decision_policies):

        ## SUPPLY CHAIN SETUP
        # ASSUMPTIONS:
        # 1. Only one product is tracked in this system.
        # 2. Any agent can have any number of suppliers and customers

        # Agent initialization
        self.sim_periods = sim_periods  # Number of periods that the simulation runs for
        self.hospitals = hospitals
        self.wholesalers = wholesalers
        self.manufacturers = manufacturers

        # Changes that can occur mid simulation
        self.disruption_function = disruption_function
        self.change_decision_policies = change_decision_policies

        ## PARAMETERS
        # Set sizes
        self.n_hospitals = len(self.hospitals)
        self.n_wholesalers = len(self.wholesalers)
        self.n_manufacturers = len(self.manufacturers)

        # Initialization of necessary parameters
        self.original_production_max = [self.manufacturers[i].production_max for i in range(self.n_manufacturers)]  # Needed for disruption


    ## Functions
    def enable_disruption(self, t):
        self.disruption_function(self, t)

    def enable_change_decision_policies(self, t):
        self.change_decision_policies(self, t)


    # Simulation runner function (DO NOT CHANGE THIS FUNCTION)
    def run(self):

        print("Starting simulation.")

        ## Run simulation for # sim_periods
        for t in range(self.sim_periods):


            ## Supply Chain Flow:
            ## 1. Change production capacities according to enable_disruption()
            self.enable_disruption(t)


            ## 2. Hospital Actions
            # Hospitals receive shipments in groups by wholesaler
            for w in range(self.n_wholesalers):
                wholesaler = self.wholesalers[w] # Wholesaler info
                shipments = wholesaler.deliver_shipments()  # For hospital shipment deliveries

                for h in wholesaler.customers:
                    # Hospital receives shipment (wholesaler delivers it)
                    h_idx = wholesaler.customers.index(h)
                    self.hospitals[h].receive_shipment(shipments[h_idx], wholesaler, w)  # Need wholesaler argument to get lead time

            # Then hospitals take their own actions one at a time
            for h in range(self.n_hospitals):

                # Hospital observes demand
                self.hospitals[h].observe_demand()

                # Hospital serves demand
                self.hospitals[h].serve_demand()

                # Hospital determines order amounts for all suppliers
                orders_for_wholesalers = self.hospitals[h].determine_orders(self.wholesalers)  

                # Hospitals submit orders to its suppliers
                for w in self.hospitals[h].suppliers:
                    w_idx = self.hospitals[h].suppliers.index(w)
                    # Wholesaler received order here
                    self.wholesalers[w].receive_order(orders_for_wholesalers[w_idx], h)


            ## 3. Wholesaler Actions
            ## Wholesalers receive shipments in groups by manufacturer
            for m in range(self.n_manufacturers):
                manufacturer = self.manufacturers[m] # Wholesaler info
                shipments = manufacturer.deliver_shipments()

                for w in manufacturer.customers:
                    # Wholesaler receives shipment (manufacturer delivers it)
                    w_idx = manufacturer.customers.index(w)
                    self.wholesalers[w].receive_shipment(shipments[w_idx], manufacturer, m)

            # Then wholesalers take their own actions one at a time
            for w in range(self.n_wholesalers):
                    
                # Wholesaler makes allocation decision
                self.wholesalers[w].allocation_decision()

                # Wholesaler observes the backlog (if any)
                self.wholesalers[w].observe_backlog()

                # Wholesaler sends shipments into transit
                self.wholesalers[w].send_shipments()

                # Wholesalers determine order amounds for all suppliers
                orders_for_manufacturers = self.wholesalers[w].determine_orders(self.manufacturers) 

                # Wholesaler submits orders to manufacturers
                for m in self.wholesalers[w].suppliers:
                    m_idx = self.wholesalers[w].suppliers.index(m)
                    # Wholesaler received order here
                    self.manufacturers[m].receive_order(orders_for_manufacturers[m_idx], w)

            ## 4. Manufacturer Actions
            for m in range(self.n_manufacturers):

                # Manufacturer observes production (after lead time)
                self.manufacturers[m].observe_production()

                # Manufacturer decides allocation to wholesalers
                self.manufacturers[m].allocation_decision()

                # Manufacturer observes backlog
                self.manufacturers[m].observe_backlog()

                # Manufacturer sends shipments (adds to shipment queue)
                self.manufacturers[m].send_shipments()

                # Manufacturer decides next production amount
                self.manufacturers[m].production_decision()
            

            print(f"Period: {t+1} done.")


        print('Simulation done.')

        return self