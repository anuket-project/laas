##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


class ResourceProvisioningException(Exception):
    """
    Resources could not be provisioned
    """
    pass


class ModelValidationException(Exception):
    """
    Validation before saving model returned issues
    """
    pass


class ResourceAvailabilityException(ResourceProvisioningException):
    """
    Requested resources are not *currently* available
    """
    pass


class ResourceExistenceException(ResourceAvailabilityException):
    """
    Requested resources do not exist or do not match any known resources
    """
    pass


class NonUniqueHostnameException(Exception):
    pass


class InvalidHostnameException(Exception):
    pass


class InvalidVlanConfigurationException(Exception):
    pass


class NetworkExistsException(Exception):
    pass
