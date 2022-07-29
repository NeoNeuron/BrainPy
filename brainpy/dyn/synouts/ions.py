# -*- coding: utf-8 -*-

from typing import Union, Callable, Optional

import brainpy.math as bm
from brainpy.dyn.base import SynOutput
from brainpy.initialize import parameter, Initializer
from brainpy.types import Tensor

__all__ = [
  'MgBlock',
]


class MgBlock(SynOutput):
  r"""Synaptic output based on Magnesium blocking.

  Given the synaptic conductance, the model output the post-synaptic current with

  .. math::

     I_{syn}(t) = g_{\mathrm{syn}}(t) (E - V(t)) g_{\infty}(V,[{Mg}^{2+}]_{o})

  where The fraction of channels :math:`g_{\infty}` that are not blocked by magnesium can be fitted to

  .. math::

     g_{\infty}(V,[{Mg}^{2+}]_{o}) = (1+{e}^{-\alpha V} \frac{[{Mg}^{2+}]_{o}} {\beta})^{-1}

  Here :math:`[{Mg}^{2+}]_{o}` is the extracellular magnesium concentration.

  Parameters
  ----------
  E: float, JaxArray, ndarray, callable, Initializer
    The reversal potential for the synaptic current. [mV]
  alpha: float, JaxArray, ndarray
    Binding constant. Default 0.062
  beta: float, JaxArray, ndarray, callable, Initializer
    Unbinding constant. Default 3.57
  cc_Mg: float, JaxArray, ndarray, callable, Initializer
    Concentration of Magnesium ion. Default 1.2 [mM].
  name: str
    The model name.
  """

  def __init__(
      self,
      E: Union[float, Tensor, Callable, Initializer] = 0.,
      cc_Mg: Union[float, Tensor, Callable, Initializer] = 1.2,
      alpha: Union[float, Tensor, Callable, Initializer] = 0.062,
      beta: Union[float, Tensor, Callable, Initializer] = 3.57,
      target_var: Optional[Union[str, bm.Variable]] = 'input',
      membrane_var: Union[str, bm.Variable] = 'V',
      name: str = None,
  ):
    super(MgBlock, self).__init__(name=name, target_var=target_var)
    self.E = E
    self.cc_Mg = cc_Mg
    self.alpha = alpha
    self.beta = beta
    self.membrane_var = membrane_var

  def register_master(self, master):
    super(MgBlock, self).register_master(master)
    self.E = parameter(self.E, self.master.post.num, allow_none=False)
    self.cc_Mg = parameter(self.cc_Mg, self.master.post.num, allow_none=False)
    self.alpha = parameter(self.alpha, self.master.post.num, allow_none=False)
    self.beta = parameter(self.beta, self.master.post.num, allow_none=False)

    if isinstance(self.membrane_var, str):
      if not hasattr(self.master.post, self.membrane_var):
        raise KeyError(f'Post-synaptic group does not have membrane variable: {self.membrane_var}')
      self.membrane_var = getattr(self.master.post, self.membrane_var)
    elif isinstance(self.membrane_var, bm.Variable):
      self.membrane_var = self.membrane_var
    else:
      raise TypeError('"membrane_var" must be instance of string or Variable. '
                      f'But we got {type(self.membrane_var)}')

  def filter(self, g):
    V = self.membrane_var.value
    I = g * (self.E - V) / (1 + self.cc_Mg / self.beta * bm.exp(-self.alpha * V))
    return super(MgBlock, self).filter(I)
