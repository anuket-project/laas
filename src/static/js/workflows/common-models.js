/*
common-models.js
Defines classes used by the workflows
Functions as the "model" part of MVC
*/

// Provided by the LibLaaS API
// TemplateBlob classes
class TemplateBlob {
    constructor(incomingBlob) {
        this.id = incomingBlob.id; // UUID (String)
        this.owner = incomingBlob.owner; // String
        this.lab_name = incomingBlob.lab_name; // String
        this.pod_name = incomingBlob.pod_name; // String
        this.pod_desc = incomingBlob.pod_desc; // String
        this["public"] = incomingBlob["public"]; // bool
        this.host_list = []; // List<HostConfigBlob>
        this.networks = []; // List<NetworkBlob>

        if (incomingBlob.host_list) {
            this.host_list = incomingBlob.host_list;
        }

        if (incomingBlob.networks) {
            this.networks = incomingBlob.networks;
        }
    }

    /**
     * Takes a network name (string) and returns the network stored in the template, or null if it does not exist
     * @param {String} network_name 
     */
    findNetwork(network_name) {
        for (const network of this.networks) {
            if (network.name == network_name) {
                return network;
            }
        }

        // Did not find it
        return null;
    }


    /**
     * Takes a hostname (string) and returns the host stored in the template, or null if it does not exist
     * @param {String} hostname
     */
        findHost(hostname) {
            for (const host of this.host_list) {
                if (host.hostname == hostname) {
                    return host;
                }
            }
    
            // Did not find it
            return null;
        }
}

class HostConfigBlob {
    constructor(incomingBlob) {
        this.hostname = incomingBlob.hostname; // String 
        this.flavor = incomingBlob.flavor; // UUID (String)
        this.image = incomingBlob.image; // UUID (String)
        this.cifile = []; // List<String>
        this.bondgroups = []; // List<BondgroupBlob>

        if (incomingBlob.cifile) {
            this.cifile = incomingBlob.cifile;
        }

        if (incomingBlob.bondgroups) {
            this.bondgroups = incomingBlob.bondgroups;
        }
    }
}

class NetworkBlob {
    constructor(incomingBlob) {
        this.name = incomingBlob.name;
        this['public'] = incomingBlob['public'];

    }
}

/** One bondgroup per interface at this time. */
class BondgroupBlob {
    constructor(incomingBlob) {
        this.connections = []; //List<ConnectionBlob>
        this.ifaces = []; // List<IfaceBlob> (will only contain the one iface for now)

        if (incomingBlob.connections) {
            this.connections = incomingBlob.connections;
        }

        if (incomingBlob.ifaces) {
            this.ifaces = incomingBlob.ifaces;
        }
    }

}

class ConnectionBlob {
    constructor(incomingBlob) {
        this.tagged = incomingBlob.tagged; // bool,
        this.connects_to = incomingBlob.connects_to; // String
    }
}

class InterfaceBlob {
    constructor(incomingBlob) {
        this.name = incomingBlob.name; // String,
        this.speed = incomingBlob.speed;
        this.cardtype = incomingBlob.cardtype;
    }
}

// BookingClasses
class BookingBlob {
    // constructor({template_id, allowed_users, global_cifile}) {
        constructor(incomingBlob) {

        this.template_id = incomingBlob.template_id; // UUID (String)
        this.allowed_users = []; // List<String>
        this.global_cifile = ""; // String
        this.metadata = new BookingMetaDataBlob({});

        if (incomingBlob.allowed_users) {
            this.allowed_users = incomingBlob.allowed_users;
        }

        if (incomingBlob.global_cifile) {
            this.global_cifile = incomingBlob.global_cifile;
        }

        if (incomingBlob.metadata) {
            this.metadata = incomingBlob.metadata;
        }
    }
}


class BookingMetaDataBlob {
    constructor(incomingBlob) {
        this.booking_id = incomingBlob.booking_id; // String
        this.owner = incomingBlob.owner; // String
        this.lab = incomingBlob.lab; // String
        this.purpose = incomingBlob.purpose; // String
        this.project = incomingBlob.project; // String
        this.length = 1 // Number

        if (incomingBlob.length) {
            this.length = incomingBlob.length;
        }
    }
}

// Utility Classes
class ImageBlob {
    constructor(incomingBlob) {
        this.image_id = incomingBlob.image_id; // UUID (String)
        this.name = incomingBlob.name; // String,
    }
}

class FlavorBlob {
    constructor(incomingBlob) {
        this.flavor_id = incomingBlob.flavor_id; // UUID (String)
        this.name = incomingBlob.name; // String
        this.interfaces = []; // List<String>
        // images are added after

        if (incomingBlob.interfaces) {
            this.interfaces = incomingBlob.interfaces;
        }
    }

}

class LabBlob {
    constructor(incomingBlob) {
        this.name = incomingBlob.name; // String
        this.description = incomingBlob.description; // String
        this.location = incomingBlob.location; //String
        this.status = incomingBlob.status; // Number

    }
}