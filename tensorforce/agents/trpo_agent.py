# Copyright 2017 reinforce.io. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from tensorforce import TensorForceError
from tensorforce.agents import Agent
from tensorforce.models import PGProbRatioModel


class TRPOAgent(Agent):
    """
    Trust Region Policy Optimization ([Schulman et al., 2015](https://arxiv.org/abs/1502.05477)) agent.
    """

    def __init__(
        self,
        states_spec,
        actions_spec,
        network,
        device=None,
        session_config=None,
        scope='trpo',
        saver_spec=None,
        summary_spec=None,
        distributed_spec=None,
        variable_noise=None,
        states_preprocessing=None,
        actions_exploration=None,
        reward_preprocessing=None,
        memory=None,
        update_spec=None,
        discount=0.99,
        distributions=None,
        entropy_regularization=None,
        baseline_mode=None,
        baseline=None,
        baseline_optimizer=None,
        gae_lambda=None,
        likelihood_ratio_clipping=None,
        batched_observe=None,  # !!!!!!!!!!!!!
        batch_size=10,
        update_frequency=None,
        learning_rate=1e-3,
        cg_max_iterations=20,
        cg_damping=1e-3,
        cg_unroll_loop=False,
        ls_max_iterations=10,
        ls_accept_ratio=0.9,
        ls_unroll_loop=False
    ):
        """
        Creates a Trust Region Policy Optimization ([Schulman et al., 2015](https://arxiv.org/abs/1502.05477)) agent.

        Args:
            states_spec: Dict containing at least one state definition. In the case of a single state,
               keys `shape` and `type` are necessary. For multiple states, pass a dict of dicts where each state
               is a dict itself with a unique name as its key.
            actions_spec: Dict containing at least one action definition. Actions have types and either `num_actions`
                for discrete actions or a `shape` for continuous actions. Consult documentation and tests for more.
            network_spec: List of layers specifying a neural network via layer types, sizes and optional arguments
                such as activation or regularisation. Full examples are in the examples/configs folder.
            device: Device string specifying model device.
            session_config: optional tf.ConfigProto with additional desired session configurations
            scope: TensorFlow scope, defaults to agent name (e.g. `dqn`).
            saver_spec: Dict specifying automated saving. Use `directory` to specify where checkpoints are saved. Use
                either `seconds` or `steps` to specify how often the model should be saved. The `load` flag specifies
                if a model is initially loaded (set to True) from a file `file`.
            summary_spec: Dict specifying summaries for TensorBoard. Requires a 'directory' to store summaries, `steps`
                or `seconds` to specify how often to save summaries, and a list of `labels` to indicate which values
                to export, e.g. `losses`, `variables`. Consult neural network class and model for all available labels.
            distributed_spec: Dict specifying distributed functionality. Use `parameter_server` and `replica_model`
                Boolean flags to indicate workers and parameter servers. Use a `cluster_spec` key to pass a TensorFlow
                cluster spec.
            discount: Float specifying reward discount factor.
            variable_noise: Experimental optional parameter specifying variable noise (NoisyNet).
            states_preprocessing_spec: Optional list of states preprocessors to apply to state  
                (e.g. `image_resize`, `grayscale`).
            actions_exploration_spec: Optional dict specifying action exploration type (epsilon greedy  
                or Gaussian noise).
            reward_preprocessing_spec: Optional dict specifying reward preprocessing.
            distributions_spec: Optional dict specifying action distributions to override default distribution choices.
                Must match action names.
            entropy_regularization: Optional positive float specifying an entropy regularization value.
            baseline_mode: String specifying baseline mode, `states` for a separate baseline per state, `network`
                for sharing parameters with the training network.
            baseline: Optional dict specifying baseline type (e.g. `mlp`, `cnn`), and its layer sizes. Consult
             examples/configs for full example configurations.
            baseline_optimizer: Optional dict specifying an optimizer and its parameters for the baseline
                following the same conventions as the main optimizer.
            gae_lambda: Optional float specifying lambda parameter for generalized advantage estimation.
            batched_observe: Optional int specifying how many observe calls are batched into one session run.
                Without batching, throughput will be lower because every `observe` triggers a session invocation to
                update rewards in the graph.
            batch_size: Int specifying number of samples collected via `observe` before an update is executed.
            keep_last_timestep: Boolean flag specifying whether last sample is kept, default True.
            likelihood_ratio_clipping: Optional clipping of likelihood ratio between old and new policy.
            learning_rate: Learning rate which may be interpreted differently according to optimizer, e.g. a natural
                gradient optimizer interprets the learning rate as the max kl-divergence between old and updated policy.
            cg_max_iterations: Int > 0 specifying conjugate gradient iterations, typically 10-20 are sufficient to
                find effective approximate solutions.
            cg_damping: Conjugate gradient damping value to increase numerical stability.
            cg_unroll_loop: Boolean indicating whether loop unrolling in TensorFlow is to be used which seems to
                impact performance negatively at this point, default False.
        """
        if network is None:
            raise TensorForceError("No network provided.")

        if memory is None:
            memory = dict(
                type='latest',
                include_next_states=False,
                capacity=(1000 * batch_size)  # assumed episode length of 1000
            )
        else:
            assert not memory['include_next_states']
        if update_frequency is None:
            update_frequency = batch_size
        update_spec = dict(
            mode='episodes',
            batch_size=batch_size,
            frequency=update_frequency
        )
        optimizer = dict(
            type='optimized_step',
            optimizer=dict(
                type='natural_gradient',
                learning_rate=learning_rate,
                cg_max_iterations=cg_max_iterations,
                cg_damping=cg_damping,
                cg_unroll_loop=cg_unroll_loop,
            ),
            ls_max_iterations=ls_max_iterations,
            ls_accept_ratio=ls_accept_ratio,
            ls_mode='exponential',  # !!!!!!!!!!!!!
            ls_parameter=0.5,  # !!!!!!!!!!!!!
            ls_unroll_loop=ls_unroll_loop
        )

        self.device = device
        self.session_config = session_config
        self.scope = scope
        self.saver_spec = saver_spec
        self.summary_spec = summary_spec
        self.distributed_spec = distributed_spec
        self.variable_noise = variable_noise
        self.states_preprocessing = states_preprocessing
        self.actions_exploration = actions_exploration
        self.reward_preprocessing = reward_preprocessing
        self.memory = memory
        self.update_spec = update_spec
        self.optimizer = optimizer
        self.discount = discount
        self.network = network
        self.distributions = distributions
        self.entropy_regularization = entropy_regularization
        self.baseline_mode = baseline_mode
        self.baseline = baseline
        self.baseline_optimizer = baseline_optimizer
        self.gae_lambda = gae_lambda
        self.likelihood_ratio_clipping = likelihood_ratio_clipping

        super(TRPOAgent, self).__init__(
            states_spec=states_spec,
            actions_spec=actions_spec,
            batched_observe=batched_observe
        )

    def initialize_model(self):
        return PGProbRatioModel(
            states_spec=self.states_spec,
            actions_spec=self.actions_spec,
            device=self.device,
            session_config=self.session_config,
            scope=self.scope,
            saver_spec=self.saver_spec,
            summary_spec=self.summary_spec,
            distributed_spec=self.distributed_spec,
            discount=self.discount,
            variable_noise=self.variable_noise,
            states_preprocessing=self.states_preprocessing,
            actions_exploration=self.actions_exploration,
            reward_preprocessing=self.reward_preprocessing,
            memory=self.memory,
            update_spec=self.update_spec,
            optimizer=self.optimizer,
            network=self.network,
            distributions=self.distributions,
            entropy_regularization=self.entropy_regularization,
            baseline_mode=self.baseline_mode,
            baseline=self.baseline,
            baseline_optimizer=self.baseline_optimizer,
            gae_lambda=self.gae_lambda,
            likelihood_ratio_clipping=self.likelihood_ratio_clipping
        )
