from torch import nn
import casadi as cs
from ann_utils import feed_forward_nn,default_state_net,default_output_net,default_encoder_net
import numpy as np
import torch
import os


cwd = os.path.dirname(__file__)

y0 = torch.load(os.path.join(cwd, "norm", "y0.pt"), weights_only=False)
ystd = torch.load(os.path.join(cwd, "norm", "ystd.pt"), weights_only=False)
u0 = torch.load(os.path.join(cwd, "norm", "u0.pt"), weights_only=False)
ustd = torch.load(os.path.join(cwd, "norm", "ustd.pt"), weights_only=False)

# functions for normalization and denormalization input-output
unorm = lambda u: (u - u0) / ustd  # Normalizálás a bemenetre
ynorm = lambda y: (y - y0) / ystd  # Normalizálás a kimenetre
ydenorm = lambda y: y * ystd + y0  # Denormalizálás a kimenetre


class simple_res_net(nn.Module):
    def __init__(self, n_in=6, n_out=5, n_nodes_per_layer=64, n_hidden_layers=2, activation=nn.Tanh):
        # linear + non-linear part
        super(simple_res_net, self).__init__()
        self.net_lin = nn.Linear(n_in, n_out)
        self.n_in = n_in
        self.n_out = n_out
        if n_hidden_layers > 0:
            self.net_lin = nn.Linear(n_in, n_out, bias=False)
            self.net_non_lin = feed_forward_nn(n_in, n_out, n_nodes_per_layer=n_nodes_per_layer,
                                               n_hidden_layers=n_hidden_layers, activation=activation)
        else:
            self.net_lin = nn.Linear(n_in, n_out)
            self.net_non_lin = None

    def forward(self, x):
        if self.net_non_lin is not None:
            return self.net_lin(x) + self.net_non_lin(x)
        else:  # linear
            return self.net_lin(x)


class casadi_res_net:
    def __init__(self, torch_model):
        self.n_in = torch_model.n_in
        self.n_out = torch_model.n_out
        self.bNonlin = False

        # residual part
        self.Wr = torch_model.net_lin.weight.detach().numpy()
        self.br = torch_model.net_lin.bias.detach().numpy()
        if torch_model.net_non_lin is not None:
            self.bNonlin = True
            # input layer
            self.W_input = torch_model.net_non_lin.net[0].weight.detach().numpy()
            self.b_input = torch_model.net_non_lin.net[0].bias.detach().numpy()
            # output layer
            self.W_output = torch_model.net_non_lin.net[-1].weight.detach().numpy()
            self.b_output = torch_model.net_non_lin.net[-1].bias.detach().numpy()

            self.n_hidden_layers = int((len(torch_model.net_non_lin.net) - 3) / 2)
            self.W_array = []
            self.b_array = []
            for i in range(self.n_hidden_layers):
                self.W_array.append(torch_model.net_non_lin.net[2 + 2 * i].weight.detach().numpy())
                self.b_array.append(torch_model.net_non_lin.net[2 + 2 * i].bias.detach().numpy())

    def activation(self, x):
        # ToDo: now only tanh is implemented, should be generalized...
        return cs.tanh(x)

    def __call__(self, net_input):
        output = net_input @ self.Wr.T+ cs.repmat(self.br, 1, net_input.shape[0]).T
        if self.bNonlin:
            nonlin_output = net_input @ self.W_input.T + cs.repmat(self.b_input, 1, net_input.shape[0]).T
            nonlin_output = self.activation(nonlin_output)
            for i in range(self.n_hidden_layers):
                nonlin_output = nonlin_output @ self.W_array[i].T + cs.repmat(self.b_array[i], 1, net_input.shape[0]).T
                nonlin_output = self.activation(nonlin_output)
            nonlin_output = nonlin_output @ self.W_output.T + cs.repmat(self.b_output, 1, net_input.shape[0]).T
            output += nonlin_output
        return output


def system_step_neural(casadi_net_f,input_state,input_control):
    input_control=unorm(input_control)
    concatenated_input = cs.horzcat(input_state, input_control)
    next_state = casadi_net_f(concatenated_input)  
    return next_state


def output_mapping_neural(casadi_net_h,input_state):
    input_control=unorm(input_state)
    real_output=ydenorm(casadi_net_h(input_state))
    return real_output


def get_net_models():
    f = default_state_net(nu = 1, nx = 16)
    f.load_state_dict(state_dict=torch.load(os.path.join(cwd, "f_dict.pt"), weights_only=False))
    f.eval()
    h = default_output_net(nx=16, ny=1)
    h.load_state_dict(state_dict=torch.load(os.path.join(cwd, "h_dict.pt"), weights_only=False))
    h.eval()
    casadi_net_f = casadi_res_net(f.net)
    casadi_net_h = casadi_res_net(h.net)
    net_model={
    'f':casadi_net_f,
    'h':casadi_net_h
    }
    return net_model
    

def get_encoder():
    encoder = default_encoder_net(na=30, nb=30, nu=1, nx=16, ny=1, activation=torch.nn.ReLU, n_nodes_per_layer=32)
    encoder.load_state_dict(state_dict=torch.load(os.path.join(cwd, "encoder_dict.pt"), weights_only=False))
    encoder.eval()
    return encoder
