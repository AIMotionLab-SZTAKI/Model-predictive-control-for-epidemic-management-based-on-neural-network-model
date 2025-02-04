### How to Use the Code 

To use the code, the `test_site.py` file needs to be executed, instantiating the appropriate classes. To control the system, it is necessary to instantiate a model class and a plant class.  The former serves as the foundation for model predictive control, based on which the algorithm computes the intervention input sequence, while the latter represents the actual system response.  The control-related parameters can be found in the `parameters.py` file, such as the control horizon and the intervention intervals.  

After the appropriate parameters and classes have been instantiated, a strategy can be applied using the `shrinking_MPC` and `rolling_MPC` functions.  

## Tests and examples

This subsection presents the class instantiations and function calls used in the implementation of each test case.  


### Scenario 1  
**Test in Section 3.2.2**  
- **Model:** Compartmental description  
- **Phase:** Compartmental model without noise  
- **The intervention signal is not rounded**  
