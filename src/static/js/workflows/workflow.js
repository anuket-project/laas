/*
Defines a common interface for creating workflows
Functions as the "view" part of MVC, or the "controller" part. Not really sure tbh
*/


const HTTP = {
    GET: "GET",
    POST: "POST",
    DELETE: "DELETE",
    PUT: "PUT"
}

const endpoint = {
    LABS: "todo", // Not implemented
    FLAVORS: "flavor/",
    IMAGES: "images/",
    TEMPLATES: "template/list/[username]",
    SAVE_DESIGN_WORKFLOW: "todo", // Post MVP
    SAVE_BOOKING_WORKFLOW: "todo", // Post MVP
    MAKE_TEMPLATE: "template/create",
    DELETE_TEMPLATE: "template",
    MAKE_BOOKING: "booking/create",
}

/** Functions as a namespace for static methods that post to the dashboard, then send an HttpRequest to LibLaas, then receive the response */
class LibLaaSAPI {

    /** POSTs to dashboard, which then auths and logs the requests, makes the request to LibLaaS, and passes the result back to here.
    Treat this as a private function. Only use the async functions when outside of this class */
    static makeRequest(method, endpoint, workflow_data) {
        console.log("Making request: %s, %s, %s", method, endpoint, workflow_data.toString())
        const token = document.getElementsByName('csrfmiddlewaretoken')[0].value
        return new Promise((resolve, reject) => {// -> HttpResponse
            $.ajax(
              {
              crossDomain: true, // might need to change this back to true
              method: "POST",
              contentType: "application/json; charset=utf-8",
              dataType : 'json',
              headers: {
                'X-CSRFToken': token
            },
              data: JSON.stringify(
                {
                    "method": method,
                    "endpoint": endpoint,
                    "workflow_data": workflow_data
                }
              ),
              timeout: 10000,
              success: (response) => {
                resolve(response);
              },
              error: (response) => {
                reject(response);
              }
            }
            )
          })
    }

    static async getLabs() { // -> List<LabBlob>
        // return this.makeRequest(HTTP.GET, endpoint.LABS, {});
        let jsonObject = JSON.parse('{"name": "UNH_IOL","description": "University of New Hampshire InterOperability Lab","location": "NH","status": 0}');
        return [new LabBlob(jsonObject)];
    }

    static async getLabFlavors(lab_name) { // -> List<FlavorBlob>
        const data = await this.handleResponse(this.makeRequest(HTTP.GET, endpoint.FLAVORS, {"lab_name": lab_name}));
        let flavors = [];
        if (data) {
            for (const d of data) {
                flavors.push(new FlavorBlob(d))
            }
        } else {
            apiError("flavors")
        }
        return flavors;
        // let jsonObject = JSON.parse('{"flavor_id": "aaa-bbb-ccc", "name": "HPE Gen 9", "description": "placeholder", "interfaces": ["ens1", "ens2", "ens3"]}')
        // return [new FlavorBlob(jsonObject)];
    }

    static async getImagesForFlavor(flavor_id) {
        let full_endpoint = endpoint.FLAVORS + flavor_id + '/[username]/' + endpoint.IMAGES;
        const data =  await this.handleResponse(this.makeRequest(HTTP.GET, full_endpoint, {}));
        let images = []

        if (data) {
            for (const d of data) {
                images.push(new ImageBlob(d));
            }
        } else {
            apiError("images")
        }

        return images;
        // let jsonObject = JSON.parse('{"image_id": "111-222-333", "name": "Arch Linux"}')
        // let jsonObject2 = JSON.parse('{"image_id": "444-555-666", "name": "Oracle Linux"}')
        // return [new ImageBlob(jsonObject), new ImageBlob(jsonObject2)];
    }

    /** Doesn't need to be passed a username because django will pull this from the request */
    static async getTemplatesForUser() { // -> List<TemplateBlob>
        const data = await this.handleResponse(this.makeRequest(HTTP.GET, endpoint.TEMPLATES, {}))
        let templates = []

        if (data)
        for (const d of data) {
            templates.push(new TemplateBlob(d))
        } else {
            apiError("templates")
        }
        return templates;
        // let jsonObject = JSON.parse('{"id": "12345", "owner":"jchoquette", "lab_name":"UNH_IOL","pod_name":"test pod","pod_desc":"for e2e testing","public":false,"host_list":[{"hostname":"test-node","flavor":"1ca6169c-a857-43c6-80b7-09b608c0daec","image":"3fc3833e-7b8b-4748-ab44-eacec8d14f8b","cifile":[],"bondgroups":[{"connections":[{"tagged":true,"connects_to":"public"}],"ifaces":[{"name":"eno49","speed":{"value":10000,"unit":"BitsPerSecond"},"cardtype":"Unknown"}]}]}],"networks":[{"name":"public","public":true}]}')
        // let jsonObject2 = JSON.parse('{"id":6789,"owner":"jchoquette","lab_name":"UNH_IOL","pod_name":"Other Host","pod_desc":"Default Template","public":false,"host_list":[{"cifile":["some ci data goes here"],"hostname":"node","flavor":"aaa-bbb-ccc","image":"111-222-333", "bondgroups":[{"connections": [{"tagged": false, "connects_to": "private"}], "ifaces": [{"name": "ens2"}]}]}],"networks":[{"name": "private", "public": false}]}');

        return [new TemplateBlob(jsonObject)];
    }

    static async saveDesignWorkflow(templateBlob) { // -> bool
        templateBlob.owner = user;
        return await this.handleResponse(this.makeRequest(HTTP.PUT, endpoint.SAVE_DESIGN_WORKFLOW))
    }

    static async saveBookingWorkflow(bookingBlob) { // -> bool
        bookingBlob.owner = user;
        return await this.handleResponse(this.makeRequest(HTTP.PUT, endpoint.SAVE_BOOKING_WORKFLOW, bookingBlob));
    }

    static async makeTemplate(templateBlob) { // -> UUID or null
        templateBlob.owner = user;
        console.log(JSON.stringify(templateBlob))
        return await this.handleResponse(this.makeRequest(HTTP.POST, endpoint.MAKE_TEMPLATE, templateBlob));
    }

    static async deleteTemplate(template_id) { // -> UUID or null
        return await this.handleResponse(this.makeRequest(HTTP.DELETE, endpoint.DELETE_TEMPLATE + "/" + template_id, {}));
    }

    /** PUT to the dashboard with the bookingBlob. Dashboard will fill in lab and owner, make the django model, then hit liblaas, then come back and fill in the agg_id  */
    static async makeBooking(bookingBlob) {
        return await this.handleResponse(this.createDashboardBooking(bookingBlob));
    }

    /** Wraps a call in a try / catch, processes the result, and returns the response or null if it failed */
    static async handleResponse(promise) {
        try {
            let x = await promise;
            return x;
        } catch(e) {
            console.log(e)
            return null;
        }
    }

    /** Uses PUT instead of POST to tell the dashboard that we want to create a dashboard booking instead of a liblaas request */
    static createDashboardBooking(bookingBlob) {
        const token = document.getElementsByName('csrfmiddlewaretoken')[0].value
        return new Promise((resolve, reject) => { // -> HttpResponse
            $.ajax(
              {
              crossDomain: false,
              method: "PUT",
              contentType: "application/json; charset=utf-8",
              dataType : 'json',
              headers: {
                'X-CSRFToken': token
            },
              data: JSON.stringify(
                bookingBlob),
              timeout: 10000,
              success: (response) => {
                resolve(response);
              },
              error: (response) => {
                reject(response);
              }
            }
            )
          })
    }
}


/** Controller class that handles button inputs to navigate through the workflow and generate HTML dynamically 
 * Treat this as an abstract class and extend it in the appropriate workflow module.
*/
class Workflow {
    constructor(sections_list) {
        this.sections = []; // List of strings
        this.step = 0; // Current step of the workflow
        this.sections = sections_list;
    }

    /** Advances the workflow by one step and scrolls to that section 
     * Disables the previous button if the step becomes 0 after executing
     * Enables the next button if the step is less than sections.length after executing
    */
    goPrev() {

        if (workflow.step <= 0) {
            return;
        }

        this.step--;

        document.getElementById(this.sections[this.step]).scrollIntoView({behavior: 'smooth'});

        if (this.step == 0) {
            document.getElementById('prev').setAttribute('disabled', '');
        } else if (this.step == this.sections.length - 2) {
            document.getElementById('next').removeAttribute('disabled');
        }
    }

    goNext() {
        if (this.step >= this.sections.length - 1 ) {
            return;
        }

        this.step++;
        document.getElementById(this.sections[this.step]).scrollIntoView({behavior: 'smooth'});

        if (this.step == this.sections.length - 1) {
            document.getElementById('next').setAttribute('disabled', '');
        } else if (this.step == 1) {
            document.getElementById('prev').removeAttribute('disabled');
        }
    }

    goTo(step_number) {
        while (step_number > this.step) {
            this.goNext();
        }

        while (step_number < this.step) {
            this.goPrev();
        }
    }

}

function apiError(info) {
    showError("Unable to fetch " + info +". Please try again later or contact support.")
  }

function showError(message) {
    const text = document.getElementById('alert_modal_message');

    text.innerText = message;
    $("#alert_modal").modal('show');
}
