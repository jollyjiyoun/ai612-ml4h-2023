# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import logging

from torch.nn.parallel import DistributedDataParallel

from distributed import (
    DistributedTimeoutWrapper,
    ModuleProxyWrapper,
)

logger = logging.getLogger(__name__)

def DistributedModel(args, model, process_group, device):
    """
    Wrap a *model* to support distributed data parallel training.

    This is similar to the built-in DistributedDataParallel, but allows
    additional configuration of the DistributedDataParallel class to
    use, and also provides easier access to the wrapped model by
    forwarding requests for missing attributes to the wrapped model.

    Args:
        args (argparse.Namespace): args
        model (BaseModel): model to wrap
        process_group: the c10d process group to be used for distributed data
            parallel all-reduction
        device: device to move 
    """

    wrapped_model = DistributedDataParallel(
        module=model.to(device),
        device_ids=[args.device_id],
        output_device=args.device_id,
        broadcast_buffers=args.broadcast_buffers,
        bucket_cap_mb=args.bucket_cap_mb,
        process_group=process_group,
        find_unused_parameters=args.find_unused_parameters
    )

    # forward missing getattr and state_dict/load_state_dict to orig model
    wrapped_model = ModuleProxyWrapper(wrapped_model)

    # kill hung distributed jobs after a timeout
    if getattr(args, "heartbeat_timeout", -1) > 0:
        wrapped_model = DistributedTimeoutWrapper(
            wrapped_model, timeout = getattr(args, "heartbeat_timeout", -1)
        )

    return wrapped_model