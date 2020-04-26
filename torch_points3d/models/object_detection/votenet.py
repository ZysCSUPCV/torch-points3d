import logging
from typing import Any

from torch_points3d.models.base_model import BaseModel
from torch_points3d.applications import models
import torch_points3d.modules.VoteNet as votenet_module
from torch_points3d.models.base_architectures import UnetBasedModel
from torch_points3d.datasets.segmentation import IGNORE_LABEL

log = logging.getLogger(__name__)


class VoteNetModel(BaseModel):
    def __init__(self, option, model_type, dataset, modules):
        """Initialize this model class.
        Parameters:
            opt -- training/test options
        A few things can be done here.
        - (required) call the initialization function of BaseModel
        - define loss function, visualization images, model names, and optimizers
        """
        super(VoteNetModel, self).__init__(option)

        # 1 - CREATE BACKBONE MODEL
        input_nc = dataset.feature_dimension

        backbone_option = option.backbone
        backbone_cls = getattr(models, backbone_option.model_type)
        self.backbone_model = backbone_cls(architecture="unet", input_nc=input_nc, config=option.backbone)

        # 2 - CREATE VOTING MODEL
        voting_option = option.voting
        voting_cls = getattr(votenet_module, voting_option.module_name)
        self.voting_module = voting_cls(vote_factor=voting_option.vote_factor, seed_feature_dim=voting_option.feat_dim)

        # 3 - CREATE PROPOSAL MODULE
        proposal_option = option.proposal
        proposal_cls = getattr(votenet_module, proposal_option.module_name)
        self.proposal_cls_module = proposal_cls(
            num_class=proposal_option.num_class,
            vote_aggregation_config=proposal_option.vote_aggregation,
            num_heading_bin=proposal_option.num_heading_bin,
            num_size_cluster=proposal_option.num_size_cluster,
            mean_size_arr=proposal_option.mean_size_arr,
            num_proposal=proposal_option.num_proposal,
            sampling=proposal_option.sampling,
        )

    def set_input(self, data, device):
        """Unpack input data from the dataloader and perform necessary pre-processing steps.
        Parameters:
            input: a dictionary that contains the data itself and its metadata information.
        """
        # Forward through backbone model

        self.backbone_model.set_input(data, device)

    def forward(self) -> Any:
        """Run forward pass. This will be called by both functions <optimize_parameters> and <test>."""

        data_features = self.backbone_model.forward()
        data_votes = self.voting_module(data_features)
        self.proposal_cls_module(data_votes)

    def backward(self):
        """Calculate losses, gradients, and update network weights; called in every training iteration"""