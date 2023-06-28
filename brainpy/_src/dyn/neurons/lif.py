from functools import partial
from typing import Union, Callable, Optional, Any, Sequence

from jax.lax import stop_gradient

import brainpy.math as bm
from brainpy._src.context import share
from brainpy._src.initialize import ZeroInit, OneInit
from brainpy._src.integrators import odeint, JointEq
from brainpy.check import is_initializer
from brainpy.types import Shape, ArrayType, Sharding
from brainpy._src.dyn._docs import ref_doc, lif_doc, pneu_doc, dpneu_doc, ltc_doc, if_doc
from brainpy._src.dyn.base import GradNeuDyn

__all__ = [
  'IF',
  'IFLTC',
  'Lif',
  'LifLTC',
  'LifRef',
  'LifRefLTC',
  'ExpIF',
  'ExpIFLTC',
  'ExpIFRef',
  'ExpIFRefLTC',
  'AdExIF',
  'AdExIFLTC',
  'AdExIFRef',
  'AdExIFRefLTC',
  'QuaIF',
  'QuaIFLTC',
  'QuaIFRef',
  'QuaIFRefLTC',
  'AdQuaIF',
  'AdQuaIFLTC',
  'AdQuaIFRef',
  'AdQuaIFRefLTC',
  'Gif',
  'GifLTC',
  'GifRef',
  'GifRefLTC',
  'Izhikevich',
  'IzhikevichLTC',
  'IzhikevichRef',
  'IzhikevichRefLTC',
]


class IFLTC(GradNeuDyn):
  r"""Leaky Integrator Model %s.

  **Model Descriptions**

  This class implements a leaky integrator model, in which its dynamics is
  given by:

  .. math::

     \tau \frac{dV}{dt} = - (V(t) - V_{rest}) + RI(t)

  where :math:`V` is the membrane potential, :math:`V_{rest}` is the resting
  membrane potential, :math:`\tau` is the time constant, and :math:`R` is the
  resistance.

  Args:
    %s
    %s
    %s
  """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = 0.,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)

    # parameters
    self.V_rest = self.init_param(V_rest)
    self.tau = self.init_param(tau)
    self.R = self.init_param(R)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def derivative(self, V, t, I):
    for out in self.cur_inputs.values():
      I += out(V)
    return (-V + self.V_rest + self.R * I) / self.tau

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    self.V.value = self.integral(self.V.value, t, x, dt)
    return self.V.value

  def return_info(self):
    return self.V


class IF(IFLTC):
  def derivative(self, V, t, I):
    return (-V + self.V_rest + self.R * I) / self.tau

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


IF.__doc__ = IFLTC.__doc__ % ('', if_doc, pneu_doc, dpneu_doc)
IFLTC.__doc__ = IFLTC.__doc__ % (ltc_doc, if_doc, pneu_doc, dpneu_doc)


class LifLTC(GradNeuDyn):
  r"""Leaky integrate-and-fire neuron model %s.

  The formal equations of a LIF model [1]_ is given by:

  .. math::

      \tau \frac{dV}{dt} = - (V(t) - V_{rest}) + RI(t) \\
      \text{after} \quad V(t) \gt V_{th}, V(t) = V_{reset}

  where :math:`V` is the membrane potential, :math:`V_{rest}` is the resting
  membrane potential, :math:`V_{reset}` is the reset membrane potential,
  :math:`V_{th}` is the spike threshold, :math:`\tau` is the time constant,
  and :math:`I` is the time-variant synaptic inputs.

  .. [1] Abbott, Larry F. "Lapicque’s introduction of the integrate-and-fire model
         neuron (1907)." Brain research bulletin 50, no. 5-6 (1999): 303-304.

  Args:
    %s
    %s
    %s

  """

  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = 0.,
      V_reset: Union[float, ArrayType, Callable] = -5.,
      V_th: Union[float, ArrayType, Callable] = 20.,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)

    # parameters
    self.V_rest = self.init_param(V_rest)
    self.V_reset = self.init_param(V_reset)
    self.V_th = self.init_param(V_th)
    self.tau = self.init_param(tau)
    self.R = self.init_param(R)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def derivative(self, V, t, I):
    for out in self.cur_inputs.values():
      I += out(V)
    return (-V + self.V_rest + self.R * I) / self.tau

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V = self.integral(self.V.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)

    self.V.value = V
    self.spike.value = spike
    return spike

  def return_info(self):
    return self.spike


class Lif(LifLTC):
  def derivative(self, V, t, I):
    return (-V + self.V_rest + self.R * I) / self.tau

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


Lif.__doc__ = LifLTC.__doc__ % ('', lif_doc, pneu_doc, dpneu_doc)
LifLTC.__doc__ = LifLTC.__doc__ % (ltc_doc, lif_doc, pneu_doc, dpneu_doc)


class LifRefLTC(LifLTC):
  r"""Leaky integrate-and-fire neuron model %s which has refractory periods.

  The formal equations of a LIF model [1]_ is given by:

  .. math::

      \tau \frac{dV}{dt} = - (V(t) - V_{rest}) + RI(t) \\
      \text{after} \quad V(t) \gt V_{th}, V(t) = V_{reset} \quad
      \text{last} \quad \tau_{ref} \quad  \text{ms}

  where :math:`V` is the membrane potential, :math:`V_{rest}` is the resting
  membrane potential, :math:`V_{reset}` is the reset membrane potential,
  :math:`V_{th}` is the spike threshold, :math:`\tau` is the time constant,
  :math:`\tau_{ref}` is the refractory time period,
  and :math:`I` is the time-variant synaptic inputs.

  .. [1] Abbott, Larry F. "Lapicque’s introduction of the integrate-and-fire model
         neuron (1907)." Brain research bulletin 50, no. 5-6 (1999): 303-304.

  Args:
    %s
    %s
    %s
    %s

  """

  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_rest: Union[float, ArrayType, Callable] = 0.,
      V_reset: Union[float, ArrayType, Callable] = -5.,
      V_th: Union[float, ArrayType, Callable] = 20.,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_rest=V_rest,
      V_reset=V_reset,
      V_th=V_th,
      R=R,
      tau=tau,
      V_initializer=V_initializer,
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e7)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V = self.integral(self.V.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike_no_grad
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class LifRef(LifRefLTC):
  def derivative(self, V, t, I):
    return (-V + self.V_rest + self.R * I) / self.tau

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


LifRef.__doc__ = LifRefLTC.__doc__ % ('', lif_doc, pneu_doc, dpneu_doc, ref_doc)
LifRefLTC.__doc__ = LifRefLTC.__doc__ % (ltc_doc, lif_doc, pneu_doc, dpneu_doc, ref_doc)


class ExpIFLTC(GradNeuDyn):
  r"""Exponential integrate-and-fire neuron model %s.

    **Model Descriptions**

    In the exponential integrate-and-fire model [1]_, the differential
    equation for the membrane potential is given by

    .. math::

        \tau\frac{d V}{d t}= - (V-V_{rest}) + \Delta_T e^{\frac{V-V_T}{\Delta_T}} + RI(t), \\
        \text{after} \, V(t) \gt V_{th}, V(t) = V_{reset} \, \text{last} \, \tau_{ref} \, \text{ms}

    This equation has an exponential nonlinearity with "sharpness" parameter :math:`\Delta_{T}`
    and "threshold" :math:`\vartheta_{rh}`.

    The moment when the membrane potential reaches the numerical threshold :math:`V_{th}`
    defines the firing time :math:`t^{(f)}`. After firing, the membrane potential is reset to
    :math:`V_{rest}` and integration restarts at time :math:`t^{(f)}+\tau_{\rm ref}`,
    where :math:`\tau_{\rm ref}` is an absolute refractory time.
    If the numerical threshold is chosen sufficiently high, :math:`V_{th}\gg v+\Delta_T`,
    its exact value does not play any role. The reason is that the upswing of the action
    potential for :math:`v\gg v +\Delta_{T}` is so rapid, that it goes to infinity in
    an incredibly short time. The threshold :math:`V_{th}` is introduced mainly for numerical
    convenience. For a formal mathematical analysis of the model, the threshold can be pushed
    to infinity.

    The model was first introduced by Nicolas Fourcaud-Trocmé, David Hansel, Carl van Vreeswijk
    and Nicolas Brunel [1]_. The exponential nonlinearity was later confirmed by Badel et al. [3]_.
    It is one of the prominent examples of a precise theoretical prediction in computational
    neuroscience that was later confirmed by experimental neuroscience.

    Two important remarks:

    - (i) The right-hand side of the above equation contains a nonlinearity
      that can be directly extracted from experimental data [3]_. In this sense the exponential
      nonlinearity is not an arbitrary choice but directly supported by experimental evidence.
    - (ii) Even though it is a nonlinear model, it is simple enough to calculate the firing
      rate for constant input, and the linear response to fluctuations, even in the presence
      of input noise [4]_.

    **Model Examples**

    .. plot::
      :include-source: True

      >>> import brainpy as bp
      >>> group = bp.neurons.ExpIF(1)
      >>> runner = bp.DSRunner(group, monitors=['V'], inputs=('input', 10.))
      >>> runner.run(300., )
      >>> bp.visualize.line_plot(runner.mon.ts, runner.mon.V, ylabel='V', show=True)


    **Model Parameters**

    ============= ============== ======== ===================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- ---------------------------------------------------
    V_rest        -65            mV       Resting potential.
    V_reset       -68            mV       Reset potential after spike.
    V_th          -30            mV       Threshold potential of spike.
    V_T           -59.9          mV       Threshold potential of generating action potential.
    delta_T       3.48           \        Spike slope factor.
    R             1              \        Membrane resistance.
    tau           10             \        Membrane time constant. Compute by R * C.
    tau_ref       1.7            \        Refractory period length.
    ============= ============== ======== ===================================================

    **Model Variables**

    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    V                  0                 Membrane potential.
    input              0                 External and synaptic input current.
    spike              False             Flag to mark whether the neuron is spiking.
    refractory         False             Flag to mark whether the neuron is in refractory period.
    t_last_spike       -1e7              Last spike time stamp.
    ================== ================= =========================================================

    **References**

    .. [1] Fourcaud-Trocmé, Nicolas, et al. "How spike generation
           mechanisms determine the neuronal response to fluctuating
           inputs." Journal of Neuroscience 23.37 (2003): 11628-11640.
    .. [2] Gerstner, W., Kistler, W. M., Naud, R., & Paninski, L. (2014).
           Neuronal dynamics: From single neurons to networks and models
           of cognition. Cambridge University Press.
    .. [3] Badel, Laurent, Sandrine Lefort, Romain Brette, Carl CH Petersen,
           Wulfram Gerstner, and Magnus JE Richardson. "Dynamic IV curves
           are reliable predictors of naturalistic pyramidal-neuron voltage
           traces." Journal of Neurophysiology 99, no. 2 (2008): 656-666.
    .. [4] Richardson, Magnus JE. "Firing-rate response of linear and nonlinear
           integrate-and-fire neurons to modulated current-based and
           conductance-based synaptic drive." Physical Review E 76, no. 2 (2007): 021919.
    .. [5] https://en.wikipedia.org/wiki/Exponential_integrate-and-fire
    """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_T: Union[float, ArrayType, Callable] = -59.9,
      delta_T: Union[float, ArrayType, Callable] = 3.48,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)
    # parameters
    self.V_rest = self.init_param(V_rest)
    self.V_reset = self.init_param(V_reset)
    self.V_th = self.init_param(V_th)
    self.V_T = self.init_param(V_T)
    self.delta_T = self.init_param(delta_T)
    self.tau = self.init_param(tau)
    self.R = self.init_param(R)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def derivative(self, V, t, I):
    for out in self.cur_inputs.values():
      I += out(V)
    exp_v = self.delta_T * bm.exp((V - self.V_T) / self.delta_T)
    dvdt = (- (V - self.V_rest) + exp_v + self.R * I) / self.tau
    return dvdt

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V = self.integral(self.V.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)

    self.V.value = V
    self.spike.value = spike
    return spike

  def return_info(self):
    return self.spike


class ExpIF(ExpIFLTC):
  def derivative(self, V, t, I):
    exp_v = self.delta_T * bm.exp((V - self.V_T) / self.delta_T)
    dvdt = (- (V - self.V_rest) + exp_v + self.R * I) / self.tau
    return dvdt

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)



class ExpIFRefLTC(ExpIFLTC):
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_T: Union[float, ArrayType, Callable] = -59.9,
      delta_T: Union[float, ArrayType, Callable] = 3.48,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_rest=V_rest,
      V_reset=V_reset,
      V_th=V_th,
      V_T=V_T,
      delta_T=delta_T,
      R=R,
      tau=tau,
      V_initializer=V_initializer,
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e7)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V = self.integral(self.V.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike_no_grad
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class ExpIFRef(ExpIFRefLTC):
  def derivative(self, V, t, I):
    exp_v = self.delta_T * bm.exp((V - self.V_T) / self.delta_T)
    dvdt = (- (V - self.V_rest) + exp_v + self.R * I) / self.tau
    return dvdt

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)

ExpIF.__doc__ = ExpIFLTC.__doc__ % ('')
ExpIFRefLTC.__doc__ = ExpIFLTC.__doc__ % (ltc_doc)
ExpIFRef.__doc__ = ExpIFLTC.__doc__ % ('')
ExpIFLTC.__doc__ = ExpIFLTC.__doc__ % (ltc_doc)


class AdExIFLTC(GradNeuDyn):
  r"""Adaptive exponential integrate-and-fire neuron model %s.

  **Model Descriptions**

  The **adaptive exponential integrate-and-fire model**, also called AdEx, is a
  spiking neuron model with two variables [1]_ [2]_.

  .. math::

      \begin{aligned}
      \tau_m\frac{d V}{d t} &= - (V-V_{rest}) + \Delta_T e^{\frac{V-V_T}{\Delta_T}} - Rw + RI(t), \\
      \tau_w \frac{d w}{d t} &=a(V-V_{rest}) - w
      \end{aligned}

  once the membrane potential reaches the spike threshold,

  .. math::

      V \rightarrow V_{reset}, \\
      w \rightarrow w+b.

  The first equation describes the dynamics of the membrane potential and includes
  an activation term with an exponential voltage dependence. Voltage is coupled to
  a second equation which describes adaptation. Both variables are reset if an action
  potential has been triggered. The combination of adaptation and exponential voltage
  dependence gives rise to the name Adaptive Exponential Integrate-and-Fire model.

  The adaptive exponential integrate-and-fire model is capable of describing known
  neuronal firing patterns, e.g., adapting, bursting, delayed spike initiation,
  initial bursting, fast spiking, and regular spiking.

  **Model Examples**

  - `Examples for different firing patterns <https://brainpy-examples.readthedocs.io/en/latest/neurons/Gerstner_2005_AdExIF_model.html>`_

  **Model Parameters**

  ============= ============== ======== ========================================================================================================================
  **Parameter** **Init Value** **Unit** **Explanation**
  ------------- -------------- -------- ------------------------------------------------------------------------------------------------------------------------
  V_rest        -65            mV       Resting potential.
  V_reset       -68            mV       Reset potential after spike.
  V_th          -30            mV       Threshold potential of spike and reset.
  V_T           -59.9          mV       Threshold potential of generating action potential.
  delta_T       3.48           \        Spike slope factor.
  a             1              \        The sensitivity of the recovery variable :math:`u` to the sub-threshold fluctuations of the membrane potential :math:`v`
  b             1              \        The increment of :math:`w` produced by a spike.
  R             1              \        Membrane resistance.
  tau           10             ms       Membrane time constant. Compute by R * C.
  tau_w         30             ms       Time constant of the adaptation current.
  tau_ref       0.             ms       Refractory time.
  ============= ============== ======== ========================================================================================================================

  **Model Variables**

  ================== ================= =========================================================
  **Variables name** **Initial Value** **Explanation**
  ------------------ ----------------- ---------------------------------------------------------
  V                   0                 Membrane potential.
  w                   0                 Adaptation current.
  input               0                 External and synaptic input current.
  spike               False             Flag to mark whether the neuron is spiking.
  refractory          False             Flag to mark whether the neuron is in refractory period.
  t_last_spike        -1e7              Last spike time stamp.
  ================== ================= =========================================================

  **References**

  .. [1] Fourcaud-Trocmé, Nicolas, et al. "How spike generation
         mechanisms determine the neuronal response to fluctuating
         inputs." Journal of Neuroscience 23.37 (2003): 11628-11640.
  .. [2] http://www.scholarpedia.org/article/Adaptive_exponential_integrate-and-fire_model
  """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_T: Union[float, ArrayType, Callable] = -59.9,
      delta_T: Union[float, ArrayType, Callable] = 3.48,
      a: Union[float, ArrayType, Callable] = 1.,
      b: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      tau_w: Union[float, ArrayType, Callable] = 30.,
      R: Union[float, ArrayType, Callable] = 1.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
      w_initializer: Union[Callable, ArrayType] = ZeroInit(),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)
    # parameters
    self.V_rest = self.init_param(V_rest)
    self.V_reset = self.init_param(V_reset)
    self.V_th = self.init_param(V_th)
    self.V_T = self.init_param(V_T)
    self.a = self.init_param(a)
    self.b = self.init_param(b)
    self.R = self.init_param(R)
    self.delta_T = self.init_param(delta_T)
    self.tau = self.init_param(tau)
    self.tau_w = self.init_param(tau_w)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._w_initializer = is_initializer(w_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def dV(self, V, t, w, I):
    for out in self.cur_inputs.values():
      I += out(V)
    exp = self.delta_T * bm.exp((V - self.V_T) / self.delta_T)
    dVdt = (- V + self.V_rest + exp - self.R * w + self.R * I) / self.tau
    return dVdt

  def dw(self, w, t, V):
    dwdt = (self.a * (V - self.V_rest) - w) / self.tau_w
    return dwdt

  @property
  def derivative(self):
    return JointEq([self.dV, self.dw])

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    self.w = self.init_variable(self._w_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V, w = self.integral(self.V.value, self.w.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike
      w += self.b * spike

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      w = bm.where(spike, w + self.b, w)

    self.V.value = V
    self.w.value = w
    self.spike.value = spike
    return spike

  def return_info(self):
    return self.spike


class AdExIF(AdExIFLTC):
  def dV(self, V, t, w, I):
    exp = self.delta_T * bm.exp((V - self.V_T) / self.delta_T)
    dVdt = (- V + self.V_rest + exp - self.R * w + self.R * I) / self.tau
    return dVdt

  def dw(self, w, t, V):
    dwdt = (self.a * (V - self.V_rest) - w) / self.tau_w
    return dwdt

  @property
  def derivative(self):
    return JointEq([self.dV, self.dw])

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


class AdExIFRefLTC(AdExIFLTC):
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_T: Union[float, ArrayType, Callable] = -59.9,
      delta_T: Union[float, ArrayType, Callable] = 3.48,
      a: Union[float, ArrayType, Callable] = 1.,
      b: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      tau_w: Union[float, ArrayType, Callable] = 30.,
      R: Union[float, ArrayType, Callable] = 1.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
      w_initializer: Union[Callable, ArrayType] = ZeroInit(),

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_rest=V_rest,
      V_reset=V_reset,
      V_th=V_th,
      V_T=V_T,
      delta_T=delta_T,
      a=a,
      b=b,
      R=R,
      tau=tau,
      tau_w=tau_w,
      V_initializer=V_initializer,
      w_initializer=w_initializer
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._w_initializer = is_initializer(w_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e8)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V, w = self.integral(self.V.value, self.w.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike_no_grad
      w += self.b * spike_no_grad
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      w = bm.where(spike, w + self.b, w)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.w.value = w
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class AdExIFRef(AdExIFRefLTC):
  def dV(self, V, t, w, I):
    exp = self.delta_T * bm.exp((V - self.V_T) / self.delta_T)
    dVdt = (- V + self.V_rest + exp - self.R * w + self.R * I) / self.tau
    return dVdt

  def dw(self, w, t, V):
    dwdt = (self.a * (V - self.V_rest) - w) / self.tau_w
    return dwdt

  @property
  def derivative(self):
    return JointEq([self.dV, self.dw])

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)

AdExIF.__doc__ = AdExIFLTC.__doc__ % ('')
AdExIFRefLTC.__doc__ = AdExIFLTC.__doc__ % (ltc_doc)
AdExIFRef.__doc__ = AdExIFLTC.__doc__ % ('')
AdExIFLTC.__doc__ = AdExIFLTC.__doc__ % (ltc_doc)

class QuaIFLTC(GradNeuDyn):
  r"""Quadratic Integrate-and-Fire neuron model %s.

    **Model Descriptions**

    In contrast to physiologically accurate but computationally expensive
    neuron models like the Hodgkin–Huxley model, the QIF model [1]_ seeks only
    to produce **action potential-like patterns** and ignores subtleties
    like gating variables, which play an important role in generating action
    potentials in a real neuron. However, the QIF model is incredibly easy
    to implement and compute, and relatively straightforward to study and
    understand, thus has found ubiquitous use in computational neuroscience.

    .. math::

        \tau \frac{d V}{d t}=c(V-V_{rest})(V-V_c) + RI(t)

    where the parameters are taken to be :math:`c` =0.07, and :math:`V_c = -50 mV` (Latham et al., 2000).

    **Model Examples**

    .. plot::
      :include-source: True

      >>> import brainpy as bp
      >>>
      >>> group = bp.neurons.QuaIF(1,)
      >>>
      >>> runner = bp.DSRunner(group, monitors=['V'], inputs=('input', 20.))
      >>> runner.run(duration=200.)
      >>> bp.visualize.line_plot(runner.mon.ts, runner.mon.V, show=True)


    **Model Parameters**

    ============= ============== ======== ========================================================================================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- ------------------------------------------------------------------------------------------------------------------------
    V_rest        -65            mV       Resting potential.
    V_reset       -68            mV       Reset potential after spike.
    V_th          -30            mV       Threshold potential of spike and reset.
    V_c           -50            mV       Critical voltage for spike initiation. Must be larger than V_rest.
    c             .07            \        Coefficient describes membrane potential update. Larger than 0.
    R             1              \        Membrane resistance.
    tau           10             ms       Membrane time constant. Compute by R * C.
    tau_ref       0              ms       Refractory period length.
    ============= ============== ======== ========================================================================================================================

    **Model Variables**

    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    V                   0                 Membrane potential.
    input               0                 External and synaptic input current.
    spike               False             Flag to mark whether the neuron is spiking.
    refractory          False             Flag to mark whether the neuron is in refractory period.
    t_last_spike       -1e7               Last spike time stamp.
    ================== ================= =========================================================

    **References**

    .. [1]  P. E. Latham, B.J. Richmond, P. Nelson and S. Nirenberg
            (2000) Intrinsic dynamics in neuronal networks. I. Theory.
            J. Neurophysiology 83, pp. 808–827.
    """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_c: Union[float, ArrayType, Callable] = -50.0,
      c: Union[float, ArrayType, Callable] = 0.07,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)
    # parameters
    self.V_rest = self.init_param(V_rest)
    self.V_reset = self.init_param(V_reset)
    self.V_th = self.init_param(V_th)
    self.V_c = self.init_param(V_c)
    self.c = self.init_param(c)
    self.R = self.init_param(R)
    self.tau = self.init_param(tau)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def derivative(self, V, t, I):
    for out in self.cur_inputs.values():
      I += out(V)
    dVdt = (self.c * (V - self.V_rest) * (V - self.V_c) + self.R * I) / self.tau
    return dVdt

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V = self.integral(self.V.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)

    self.V.value = V
    self.spike.value = spike
    return spike

  def return_info(self):
    return self.spike


class QuaIF(QuaIFLTC):
  def derivative(self, V, t, I):
    dVdt = (self.c * (V - self.V_rest) * (V - self.V_c) + self.R * I) / self.tau
    return dVdt

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


class QuaIFRefLTC(QuaIFLTC):
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_c: Union[float, ArrayType, Callable] = -50.0,
      c: Union[float, ArrayType, Callable] = 0.07,
      R: Union[float, ArrayType, Callable] = 1.,
      tau: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_rest=V_rest,
      V_reset=V_reset,
      V_th=V_th,
      V_c=V_c,
      c=c,
      R=R,
      tau=tau,
      V_initializer=V_initializer,
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e7)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V = self.integral(self.V.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike_no_grad
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class QuaIFRef(QuaIFRefLTC):
  def derivative(self, V, t, I):
    dVdt = (self.c * (V - self.V_rest) * (V - self.V_c) + self.R * I) / self.tau
    return dVdt

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


QuaIF.__doc__ = QuaIFLTC.__doc__ % ('')
QuaIFRefLTC.__doc__ = QuaIFLTC.__doc__ % (ltc_doc)
QuaIFRef.__doc__ = QuaIFLTC.__doc__ % ('')
QuaIFLTC.__doc__ = QuaIFLTC.__doc__ % (ltc_doc)


class AdQuaIFLTC(GradNeuDyn):
  r"""Adaptive quadratic integrate-and-fire neuron model %s.

  **Model Descriptions**

  The adaptive quadratic integrate-and-fire neuron model [1]_ is given by:

  .. math::

      \begin{aligned}
      \tau_m \frac{d V}{d t}&=c(V-V_{rest})(V-V_c) - w + I(t), \\
      \tau_w \frac{d w}{d t}&=a(V-V_{rest}) - w,
      \end{aligned}

  once the membrane potential reaches the spike threshold,

  .. math::

      V \rightarrow V_{reset}, \\
      w \rightarrow w+b.

  **Model Examples**

  .. plot::
    :include-source: True

    >>> import brainpy as bp
    >>> group = bp.neurons.AdQuaIF(1, )
    >>> runner = bp.DSRunner(group, monitors=['V', 'w'], inputs=('input', 30.))
    >>> runner.run(300)
    >>> fig, gs = bp.visualize.get_figure(2, 1, 3, 8)
    >>> fig.add_subplot(gs[0, 0])
    >>> bp.visualize.line_plot(runner.mon.ts, runner.mon.V, ylabel='V')
    >>> fig.add_subplot(gs[1, 0])
    >>> bp.visualize.line_plot(runner.mon.ts, runner.mon.w, ylabel='w', show=True)

  **Model Parameters**

  ============= ============== ======== =======================================================
  **Parameter** **Init Value** **Unit** **Explanation**
  ------------- -------------- -------- -------------------------------------------------------
  V_rest         -65            mV       Resting potential.
  V_reset        -68            mV       Reset potential after spike.
  V_th           -30            mV       Threshold potential of spike and reset.
  V_c            -50            mV       Critical voltage for spike initiation. Must be larger
                                         than :math:`V_{rest}`.
  a               1              \       The sensitivity of the recovery variable :math:`u` to
                                         the sub-threshold fluctuations of the membrane
                                         potential :math:`v`
  b              .1             \        The increment of :math:`w` produced by a spike.
  c              .07             \       Coefficient describes membrane potential update.
                                         Larger than 0.
  tau            10             ms       Membrane time constant.
  tau_w          10             ms       Time constant of the adaptation current.
  ============= ============== ======== =======================================================

  **Model Variables**

  ================== ================= ==========================================================
  **Variables name** **Initial Value** **Explanation**
  ------------------ ----------------- ----------------------------------------------------------
  V                   0                 Membrane potential.
  w                   0                 Adaptation current.
  input               0                 External and synaptic input current.
  spike               False             Flag to mark whether the neuron is spiking.
  t_last_spike        -1e7              Last spike time stamp.
  ================== ================= ==========================================================

  **References**

  .. [1] Izhikevich, E. M. (2004). Which model to use for cortical spiking
         neurons?. IEEE transactions on neural networks, 15(5), 1063-1070.
  .. [2] Touboul, Jonathan. "Bifurcation analysis of a general class of
         nonlinear integrate-and-fire neurons." SIAM Journal on Applied
         Mathematics 68, no. 4 (2008): 1045-1079.
  """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_c: Union[float, ArrayType, Callable] = -50.0,
      a: Union[float, ArrayType, Callable] = 1.,
      b: Union[float, ArrayType, Callable] = .1,
      c: Union[float, ArrayType, Callable] = .07,
      tau: Union[float, ArrayType, Callable] = 10.,
      tau_w: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
      w_initializer: Union[Callable, ArrayType] = ZeroInit(),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)
    # parameters
    self.V_rest = self.init_param(V_rest)
    self.V_reset = self.init_param(V_reset)
    self.V_th = self.init_param(V_th)
    self.V_c = self.init_param(V_c)
    self.a = self.init_param(a)
    self.b = self.init_param(b)
    self.c = self.init_param(c)
    self.tau = self.init_param(tau)
    self.tau_w = self.init_param(tau_w)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._w_initializer = is_initializer(w_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def dV(self, V, t, w, I):
    for out in self.cur_inputs.values():
      I += out(V)
    dVdt = (self.c * (V - self.V_rest) * (V - self.V_c) - w + I) / self.tau
    return dVdt

  def dw(self, w, t, V):
    dwdt = (self.a * (V - self.V_rest) - w) / self.tau_w
    return dwdt

  @property
  def derivative(self):
    return JointEq([self.dV, self.dw])

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    self.w = self.init_variable(self._w_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V, w = self.integral(self.V.value, self.w.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike
      w += self.b * spike

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      w = bm.where(spike, w + self.b, w)

    self.V.value = V
    self.w.value = w
    self.spike.value = spike
    return spike

  def return_info(self):
    return self.spike


class AdQuaIF(AdQuaIFLTC):
  def dV(self, V, t, w, I):
    dVdt = (self.c * (V - self.V_rest) * (V - self.V_c) - w + I) / self.tau
    return dVdt

  def dw(self, w, t, V):
    dwdt = (self.a * (V - self.V_rest) - w) / self.tau_w
    return dwdt

  @property
  def derivative(self):
    return JointEq([self.dV, self.dw])

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


class AdQuaIFRefLTC(AdQuaIFLTC):
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_rest: Union[float, ArrayType, Callable] = -65.,
      V_reset: Union[float, ArrayType, Callable] = -68.,
      V_th: Union[float, ArrayType, Callable] = -30.,
      V_c: Union[float, ArrayType, Callable] = -50.0,
      a: Union[float, ArrayType, Callable] = 1.,
      b: Union[float, ArrayType, Callable] = .1,
      c: Union[float, ArrayType, Callable] = .07,
      tau: Union[float, ArrayType, Callable] = 10.,
      tau_w: Union[float, ArrayType, Callable] = 10.,
      V_initializer: Union[Callable, ArrayType] = ZeroInit(),
      w_initializer: Union[Callable, ArrayType] = ZeroInit(),

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_rest=V_rest,
      V_reset=V_reset,
      V_th=V_th,
      V_c=V_c,
      a=a,
      b=b,
      c=c,
      tau=tau,
      tau_w=tau_w,
      V_initializer=V_initializer,
      w_initializer=w_initializer
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._w_initializer = is_initializer(w_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e8)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V, w = self.integral(self.V.value, self.w.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike_no_grad
      w += self.b * spike_no_grad
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      w = bm.where(spike, w + self.b, w)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.w.value = w
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class AdQuaIFRef(AdQuaIFRefLTC):
  def dV(self, V, t, w, I):
    dVdt = (self.c * (V - self.V_rest) * (V - self.V_c) - w + I) / self.tau
    return dVdt

  def dw(self, w, t, V):
    dwdt = (self.a * (V - self.V_rest) - w) / self.tau_w
    return dwdt

  @property
  def derivative(self):
    return JointEq([self.dV, self.dw])

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


AdQuaIF.__doc__ = AdQuaIFLTC.__doc__ % ('')
AdQuaIFRefLTC.__doc__ = AdQuaIFLTC.__doc__ % (ltc_doc)
AdQuaIFRef.__doc__ = AdQuaIFLTC.__doc__ % ('')
AdQuaIFLTC.__doc__ = AdQuaIFLTC.__doc__ % (ltc_doc)


class GifLTC(GradNeuDyn):
  r"""Generalized Integrate-and-Fire model %s.

    **Model Descriptions**

    The generalized integrate-and-fire model [1]_ is given by

    .. math::

        &\frac{d I_j}{d t} = - k_j I_j

        &\frac{d V}{d t} = ( - (V - V_{rest}) + R\sum_{j}I_j + RI) / \tau

        &\frac{d V_{th}}{d t} = a(V - V_{rest}) - b(V_{th} - V_{th\infty})

    When :math:`V` meet :math:`V_{th}`, Generalized IF neuron fires:

    .. math::

        &I_j \leftarrow R_j I_j + A_j

        &V \leftarrow V_{reset}

        &V_{th} \leftarrow max(V_{th_{reset}}, V_{th})

    Note that :math:`I_j` refers to arbitrary number of internal currents.

    **Model Examples**

    - `Detailed examples to reproduce different firing patterns <https://brainpy-examples.readthedocs.io/en/latest/neurons/Niebur_2009_GIF.html>`_

    **Model Parameters**

    ============= ============== ======== ====================================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- --------------------------------------------------------------------
    V_rest        -70            mV       Resting potential.
    V_reset       -70            mV       Reset potential after spike.
    V_th_inf      -50            mV       Target value of threshold potential :math:`V_{th}` updating.
    V_th_reset    -60            mV       Free parameter, should be larger than :math:`V_{reset}`.
    R             20             \        Membrane resistance.
    tau           20             ms       Membrane time constant. Compute by :math:`R * C`.
    a             0              \        Coefficient describes the dependence of
                                          :math:`V_{th}` on membrane potential.
    b             0.01           \        Coefficient describes :math:`V_{th}` update.
    k1            0.2            \        Constant pf :math:`I1`.
    k2            0.02           \        Constant of :math:`I2`.
    R1            0              \        Free parameter.
                                          Describes dependence of :math:`I_1` reset value on
                                          :math:`I_1` value before spiking.
    R2            1              \        Free parameter.
                                          Describes dependence of :math:`I_2` reset value on
                                          :math:`I_2` value before spiking.
    A1            0              \        Free parameter.
    A2            0              \        Free parameter.
    ============= ============== ======== ====================================================================

    **Model Variables**

    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    V                  -70               Membrane potential.
    input              0                 External and synaptic input current.
    spike              False             Flag to mark whether the neuron is spiking.
    V_th               -50               Spiking threshold potential.
    I1                 0                 Internal current 1.
    I2                 0                 Internal current 2.
    t_last_spike       -1e7              Last spike time stamp.
    ================== ================= =========================================================

    **References**

    .. [1] Mihalaş, Ştefan, and Ernst Niebur. "A generalized linear
           integrate-and-fire neural model produces diverse spiking
           behaviors." Neural computation 21.3 (2009): 704-718.
    .. [2] Teeter, Corinne, Ramakrishnan Iyer, Vilas Menon, Nathan
           Gouwens, David Feng, Jim Berg, Aaron Szafer et al. "Generalized
           leaky integrate-and-fire models classify multiple neuron types."
           Nature communications 9, no. 1 (2018): 1-15.
  """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_rest: Union[float, ArrayType, Callable] = -70.,
      V_reset: Union[float, ArrayType, Callable] = -70.,
      V_th_inf: Union[float, ArrayType, Callable] = -50.,
      V_th_reset: Union[float, ArrayType, Callable] = -60.,
      R: Union[float, ArrayType, Callable] = 20.,
      tau: Union[float, ArrayType, Callable] = 20.,
      a: Union[float, ArrayType, Callable] = 0.,
      b: Union[float, ArrayType, Callable] = 0.01,
      k1: Union[float, ArrayType, Callable] = 0.2,
      k2: Union[float, ArrayType, Callable] = 0.02,
      R1: Union[float, ArrayType, Callable] = 0.,
      R2: Union[float, ArrayType, Callable] = 1.,
      A1: Union[float, ArrayType, Callable] = 0.,
      A2: Union[float, ArrayType, Callable] = 0.,
      V_initializer: Union[Callable, ArrayType] = OneInit(-70.),
      I1_initializer: Union[Callable, ArrayType] = ZeroInit(),
      I2_initializer: Union[Callable, ArrayType] = ZeroInit(),
      Vth_initializer: Union[Callable, ArrayType] = OneInit(-50.),
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)
    # parameters
    self.V_rest = self.init_param(V_rest)
    self.V_reset = self.init_param(V_reset)
    self.V_th_inf = self.init_param(V_th_inf)
    self.V_th_reset = self.init_param(V_th_reset)
    self.R = self.init_param(R)
    self.a = self.init_param(a)
    self.b = self.init_param(b)
    self.k1 = self.init_param(k1)
    self.k2 = self.init_param(k2)
    self.R1 = self.init_param(R1)
    self.R2 = self.init_param(R2)
    self.A1 = self.init_param(A1)
    self.A2 = self.init_param(A2)
    self.tau = self.init_param(tau)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._I1_initializer = is_initializer(I1_initializer)
    self._I2_initializer = is_initializer(I2_initializer)
    self._Vth_initializer = is_initializer(Vth_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def dI1(self, I1, t):
    return - self.k1 * I1

  def dI2(self, I2, t):
    return - self.k2 * I2

  def dVth(self, V_th, t, V):
    return self.a * (V - self.V_rest) - self.b * (V_th - self.V_th_inf)

  def dV(self, V, t, I1, I2, I):
    for out in self.cur_inputs.values():
      I += out(V)
    return (- (V - self.V_rest) + self.R * (I + I1 + I2)) / self.tau

  @property
  def derivative(self):
    return JointEq(self.dI1, self.dI2, self.dVth, self.dV)

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    self.I1 = self.init_variable(self._I1_initializer, batch_size)
    self.I2 = self.init_variable(self._I2_initializer, batch_size)
    self.V_th = self.init_variable(self._Vth_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    I1, I2, V_th, V = self.integral(self.I1.value, self.I2.value, self.V_th.value, self.V.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike
      I1 += spike * (self.R1 * I1 + self.A1 - I1)
      I2 += spike * (self.R2 * I2 + self.A2 - I2)
      reset_th = self.spk_fun(self.V_th_reset - V_th) * spike
      V_th += reset_th * (self.V_th_reset - V_th)

    else:
      spike = self.V_th <= V
      V = bm.where(spike, self.V_reset, V)
      I1 = bm.where(spike, self.R1 * I1 + self.A1, I1)
      I2 = bm.where(spike, self.R2 * I2 + self.A2, I2)
      V_th = bm.where(spike, bm.maximum(self.V_th_reset, V_th), V_th)
    self.spike.value = spike
    self.I1.value = I1
    self.I2.value = I2
    self.V_th.value = V_th
    self.V.value = V
    return spike

  def return_info(self):
    return self.spike


class Gif(GifLTC):
  def dI1(self, I1, t):
    return - self.k1 * I1

  def dI2(self, I2, t):
    return - self.k2 * I2

  def dVth(self, V_th, t, V):
    return self.a * (V - self.V_rest) - self.b * (V_th - self.V_th_inf)

  def dV(self, V, t, I1, I2, I):
    return (- (V - self.V_rest) + self.R * (I + I1 + I2)) / self.tau

  @property
  def derivative(self):
    return JointEq(self.dI1, self.dI2, self.dVth, self.dV)

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


class GifRefLTC(GifLTC):
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_rest: Union[float, ArrayType, Callable] = -70.,
      V_reset: Union[float, ArrayType, Callable] = -70.,
      V_th_inf: Union[float, ArrayType, Callable] = -50.,
      V_th_reset: Union[float, ArrayType, Callable] = -60.,
      R: Union[float, ArrayType, Callable] = 20.,
      tau: Union[float, ArrayType, Callable] = 20.,
      a: Union[float, ArrayType, Callable] = 0.,
      b: Union[float, ArrayType, Callable] = 0.01,
      k1: Union[float, ArrayType, Callable] = 0.2,
      k2: Union[float, ArrayType, Callable] = 0.02,
      R1: Union[float, ArrayType, Callable] = 0.,
      R2: Union[float, ArrayType, Callable] = 1.,
      A1: Union[float, ArrayType, Callable] = 0.,
      A2: Union[float, ArrayType, Callable] = 0.,
      V_initializer: Union[Callable, ArrayType] = OneInit(-70.),
      I1_initializer: Union[Callable, ArrayType] = ZeroInit(),
      I2_initializer: Union[Callable, ArrayType] = ZeroInit(),
      Vth_initializer: Union[Callable, ArrayType] = OneInit(-50.),

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_rest=V_rest,
      V_reset=V_reset,
      V_th_inf=V_th_inf,
      V_th_reset=V_th_reset,
      R=R,
      a=a,
      b=b,
      k1=k1,
      k2=k2,
      R1=R1,
      R2=R2,
      A1=A1,
      A2=A2,
      tau=tau,
      V_initializer=V_initializer,
      I1_initializer=I1_initializer,
      I2_initializer=I2_initializer,
      Vth_initializer=Vth_initializer,
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._I1_initializer = is_initializer(I1_initializer)
    self._I2_initializer = is_initializer(I2_initializer)
    self._Vth_initializer = is_initializer(Vth_initializer)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e8)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    I1, I2, V_th, V = self.integral(self.I1.value, self.I2.value, self.V_th.value, self.V.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += (self.V_reset - V) * spike
      I1 += spike * (self.R1 * I1 + self.A1 - I1)
      I2 += spike * (self.R2 * I2 + self.A2 - I2)
      reset_th = self.spk_fun(self.V_th_reset - V_th) * spike
      V_th += reset_th * (self.V_th_reset - V_th)
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.V_reset, V)
      I1 = bm.where(spike, self.R1 * I1 + self.A1, I1)
      I2 = bm.where(spike, self.R2 * I2 + self.A2, I2)
      V_th = bm.where(spike, bm.maximum(self.V_th_reset, V_th), V_th)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.I1.value = I1
    self.I2.value = I2
    self.V_th.value = V_th
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class GifRef(GifRefLTC):
  def dI1(self, I1, t):
    return - self.k1 * I1

  def dI2(self, I2, t):
    return - self.k2 * I2

  def dVth(self, V_th, t, V):
    return self.a * (V - self.V_rest) - self.b * (V_th - self.V_th_inf)

  def dV(self, V, t, I1, I2, I):
    return (- (V - self.V_rest) + self.R * (I + I1 + I2)) / self.tau

  @property
  def derivative(self):
    return JointEq(self.dI1, self.dI2, self.dVth, self.dV)

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


Gif.__doc__ = GifLTC.__doc__ % ('')
GifRefLTC.__doc__ = GifLTC.__doc__ % (ltc_doc)
GifRef.__doc__ = GifLTC.__doc__ % ('')
GifLTC.__doc__ = GifLTC.__doc__ % (ltc_doc)


class IzhikevichLTC(GradNeuDyn):
  r"""The Izhikevich neuron model %s.

    **Model Descriptions**

    The dynamics of the Izhikevich neuron model [1]_ [2]_ is given by:

    .. math ::

        \frac{d V}{d t} &= 0.04 V^{2}+5 V+140-u+I

        \frac{d u}{d t} &=a(b V-u)

    .. math ::

        \text{if}  v \geq 30  \text{mV}, \text{then}
        \begin{cases} v \leftarrow c \\
        u \leftarrow u+d \end{cases}

    **Model Examples**

    - `Detailed examples to reproduce different firing patterns <https://brainpy-examples.readthedocs.io/en/latest/neurons/Izhikevich_2003_Izhikevich_model.html>`_

    **Model Parameters**

    ============= ============== ======== ================================================================================
    **Parameter** **Init Value** **Unit** **Explanation**
    ------------- -------------- -------- --------------------------------------------------------------------------------
    a             0.02           \        It determines the time scale of
                                          the recovery variable :math:`u`.
    b             0.2            \        It describes the sensitivity of the
                                          recovery variable :math:`u` to
                                          the sub-threshold fluctuations of the
                                          membrane potential :math:`v`.
    c             -65            \        It describes the after-spike reset value
                                          of the membrane potential :math:`v` caused by
                                          the fast high-threshold :math:`K^{+}`
                                          conductance.
    d             8              \        It describes after-spike reset of the
                                          recovery variable :math:`u`
                                          caused by slow high-threshold
                                          :math:`Na^{+}` and :math:`K^{+}` conductance.
    tau_ref       0              ms       Refractory period length. [ms]
    V_th          30             mV       The membrane potential threshold.
    ============= ============== ======== ================================================================================

    **Model Variables**

    ================== ================= =========================================================
    **Variables name** **Initial Value** **Explanation**
    ------------------ ----------------- ---------------------------------------------------------
    V                          -65        Membrane potential.
    u                          1          Recovery variable.
    input                      0          External and synaptic input current.
    spike                      False      Flag to mark whether the neuron is spiking.
    refractory                False       Flag to mark whether the neuron is in refractory period.
    t_last_spike               -1e7       Last spike time stamp.
    ================== ================= =========================================================

    **References**

    .. [1] Izhikevich, Eugene M. "Simple model of spiking neurons." IEEE
           Transactions on neural networks 14.6 (2003): 1569-1572.

    .. [2] Izhikevich, Eugene M. "Which model to use for cortical spiking neurons?."
           IEEE transactions on neural networks 15.5 (2004): 1063-1070.
    """
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sequence[str]] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      name: Optional[str] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      init_var: bool = True,

      # neuron parameters
      V_th: Union[float, ArrayType, Callable] = 30.,
      a: Union[float, ArrayType, Callable] = 0.02,
      b: Union[float, ArrayType, Callable] = 0.20,
      c: Union[float, ArrayType, Callable] = -65.,
      d: Union[float, ArrayType, Callable] = 8.,
      tau: Union[float, ArrayType, Callable] = 10.,
      R: Union[float, ArrayType, Callable] = 1.,
      V_initializer: Union[Callable, ArrayType] = OneInit(-70.),
      u_initializer: Union[Callable, ArrayType] = None,
  ):
    # initialization
    super().__init__(size=size,
                     name=name,
                     keep_size=keep_size,
                     mode=mode,
                     sharding=sharding,
                     spk_fun=spk_fun,
                     detach_spk=detach_spk,
                     method=method,
                     spk_type=spk_type)
    # parameters
    self.V_th = self.init_param(V_th)
    self.a = self.init_param(a)
    self.b = self.init_param(b)
    self.c = self.init_param(c)
    self.d = self.init_param(d)
    self.R = self.init_param(R)
    self.tau = self.init_param(tau)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._u_initializer = is_initializer(u_initializer, allow_none=True)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def dV(self, V, t, u, I):
    for out in self.cur_inputs.values():
      I += out(V)
    dVdt = 0.04 * V * V + 5 * V + 140 - u + I
    return dVdt

  def du(self, u, t, V):
    dudt = self.a * (self.b * V - u)
    return dudt

  @property
  def derivative(self):
    return JointEq([self.dV, self.du])

  def reset_state(self, batch_size=None):
    self.V = self.init_variable(self._V_initializer, batch_size)
    u_initializer = OneInit(self.b * self.V) if self._u_initializer is None else self._u_initializer
    self._u_initializer = is_initializer(u_initializer)
    self.u = self.init_variable(self._u_initializer, batch_size)
    self.spike = self.init_variable(partial(bm.zeros, dtype=self.spk_type), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V, u = self.integral(self.V.value, self.u.value, t, x, dt)

    # spike, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike = stop_gradient(spike) if self.detach_spk else spike
      V += spike * (self.c - self.V_th)
      u += spike * self.d

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.c, V)
      u = bm.where(spike, u + self.d, u)

    self.V.value = V
    self.u.value = u
    self.spike.value = spike
    return spike

  def return_info(self):
    return self.spike


class Izhikevich(IzhikevichLTC):
  def dV(self, V, t, u, I):
    dVdt = 0.04 * V * V + 5 * V + 140 - u + I
    return dVdt

  def du(self, u, t, V):
    dudt = self.a * (self.b * V - u)
    return dudt

  @property
  def derivative(self):
    return JointEq([self.dV, self.du])

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


class IzhikevichRefLTC(IzhikevichLTC):
  def __init__(
      self,
      size: Shape,
      sharding: Optional[Sharding] = None,
      keep_size: bool = False,
      mode: Optional[bm.Mode] = None,
      spk_fun: Callable = bm.surrogate.InvSquareGrad(),
      spk_type: Any = None,
      detach_spk: bool = False,
      method: str = 'exp_auto',
      name: Optional[str] = None,
      init_var: bool = True,

      # old neuron parameter
      V_th: Union[float, ArrayType, Callable] = 30.,
      a: Union[float, ArrayType, Callable] = 0.02,
      b: Union[float, ArrayType, Callable] = 0.20,
      c: Union[float, ArrayType, Callable] = -65.,
      d: Union[float, ArrayType, Callable] = 8.,
      tau: Union[float, ArrayType, Callable] = 10.,
      R: Union[float, ArrayType, Callable] = 1.,
      V_initializer: Union[Callable, ArrayType] = OneInit(-70.),
      u_initializer: Union[Callable, ArrayType] = None,

      # new neuron parameter
      tau_ref: Union[float, ArrayType, Callable] = 0.,
      ref_var: bool = False,
  ):
    # initialization
    super().__init__(
      size=size,
      name=name,
      keep_size=keep_size,
      mode=mode,
      method=method,
      sharding=sharding,
      spk_fun=spk_fun,
      detach_spk=detach_spk,
      spk_type=spk_type,

      init_var=False,

      V_th=V_th,
      a=a,
      b=b,
      c=c,
      d=d,
      R=R,
      tau=tau,
      V_initializer=V_initializer,
      u_initializer=u_initializer
    )

    # parameters
    self.ref_var = ref_var
    self.tau_ref = self.init_param(tau_ref)

    # initializers
    self._V_initializer = is_initializer(V_initializer)
    self._u_initializer = is_initializer(u_initializer, allow_none=True)

    # integral
    self.integral = odeint(method=method, f=self.derivative)

    # variables
    if init_var:
      self.reset_state(self.mode)

  def reset_state(self, batch_size=None):
    super().reset_state(batch_size)
    self.t_last_spike = self.init_variable(bm.ones, batch_size)
    self.t_last_spike.fill_(-1e7)
    if self.ref_var:
      self.refractory = self.init_variable(partial(bm.zeros, dtype=bool), batch_size)

  def update(self, x=None):
    t = share.load('t')
    dt = share.load('dt')
    x = 0. if x is None else x

    # integrate membrane potential
    V, u = self.integral(self.V.value, self.u.value, t, x, dt)

    # refractory
    refractory = (t - self.t_last_spike) <= self.tau_ref
    if isinstance(self.mode, bm.TrainingMode):
      refractory = stop_gradient(refractory)
    V = bm.where(refractory, self.V.value, V)

    # spike, refractory, spiking time, and membrane potential reset
    if isinstance(self.mode, bm.TrainingMode):
      spike = self.spk_fun(V - self.V_th)
      spike_no_grad = stop_gradient(spike) if self.detach_spk else spike
      V += spike * (self.c - self.V_th)
      u += spike * self.d
      spike_ = spike_no_grad > 0.
      # will be used in other place, like Delta Synapse, so stop its gradient
      if self.ref_var:
        self.refractory.value = stop_gradient(bm.logical_or(refractory, spike_).value)
      t_last_spike = stop_gradient(bm.where(spike_, t, self.t_last_spike.value))

    else:
      spike = V >= self.V_th
      V = bm.where(spike, self.c, V)
      u = bm.where(spike, u + self.d, u)
      if self.ref_var:
        self.refractory.value = bm.logical_or(refractory, spike)
      t_last_spike = bm.where(spike, t, self.t_last_spike.value)
    self.V.value = V
    self.u.value = u
    self.spike.value = spike
    self.t_last_spike.value = t_last_spike
    return spike


class IzhikevichRef(IzhikevichRefLTC):
  def dV(self, V, t, u, I):
    dVdt = 0.04 * V * V + 5 * V + 140 - u + I
    return dVdt

  def du(self, u, t, V):
    dudt = self.a * (self.b * V - u)
    return dudt

  @property
  def derivative(self):
    return JointEq([self.dV, self.du])

  def update(self, x=None):
    x = 0. if x is None else x
    for out in self.cur_inputs.values():
      x += out(self.V.value)
    super().update(x)


Izhikevich.__doc__ = IzhikevichLTC.__doc__ % ('')
IzhikevichRefLTC.__doc__ = IzhikevichLTC.__doc__ % (ltc_doc)
IzhikevichRef.__doc__ = IzhikevichLTC.__doc__ % ('')
IzhikevichLTC.__doc__ = IzhikevichLTC.__doc__ % (ltc_doc)