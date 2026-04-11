# API reference

The **source of truth for API documentation is inline docstrings in `python/brambhand/src/brambhand/`**.

This file is intentionally lightweight and points to where to read detailed API
contracts and rationale.

## How to read API docs

- Read module/class/function docstrings directly in source files under `python/brambhand/src/brambhand/`.
- Use an interactive shell:

```python
import inspect
from brambhand.physics.integrator import VelocityVerletIntegrator
print(inspect.getdoc(VelocityVerletIntegrator))
```

- Or via pydoc:

```bash
python -m pydoc brambhand.physics.integrator
```

## API module index

- `brambhand.cli`
- `brambhand.core.event_bus`
- `brambhand.core.state_snapshot`
- `brambhand.physics.vector`
- `brambhand.physics.body`
- `brambhand.physics.gravity_model`
- `brambhand.physics.integrator`
- `brambhand.spacecraft.mass_model`
- `brambhand.spacecraft.propulsion`
- `brambhand.spacecraft.command_model`
- `brambhand.guidance.orbit_elements`
- `brambhand.guidance.trajectory_predictor`
- `brambhand.communication.visibility`
- `brambhand.communication.link_model`
- `brambhand.communication.delay_channel`
- `brambhand.operations.rendezvous_metrics`
- `brambhand.operations.docking_model`
- `brambhand.operations.constellation`
- `brambhand.infrastructure.station`
- `brambhand.dynamics.rigid_body_6dof`
- `brambhand.dynamics.mechanisms`
- `brambhand.dynamics.contact_docking`
- `brambhand.dynamics.control`
- `brambhand.propulsion.fluid_network`
- `brambhand.propulsion.combustion_model`
- `brambhand.propulsion.thrust_estimator`
- `brambhand.propulsion.leakage_model`
- `brambhand.structures.fem`
- `brambhand.structures.fem.contracts`
- `brambhand.structures.fem.geometry`
- `brambhand.structures.fem.backends`
- `brambhand.structures.fem.selection`
- `brambhand.structures.fem.solver`
- `brambhand.scenario.scenario_schema`
- `brambhand.scenario.scenario_loader`
- `brambhand.scenario.replay_log`
