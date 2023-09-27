/*
Defines a common interface for creating workflows
Functions as the "view" part of MVC, or the "controller" part.
*/

const endpoint = {
    LABS: "todo", // Not implemented
    FLAVORS: "flavor/",
    IMAGES: "images/",
    TEMPLATES: "template/",
    MAKE_TEMPLATE: "template/create/",
    MAKE_BOOKING: "booking/create/",
}

/** Functions as a namespace for static methods that post to the dashboard, then send an HttpRequest to LibLaas, then receive the response */
class LibLaaSAPI {

    /** POSTs to dashboard, which then auths and logs the requests, makes the request to LibLaaS, and passes the result back to here.
    Treat this as a private function. Only use the async functions when outside of this class */
    static makeRequest(endpoint, json_data) {
        const token = document.getElementsByName('csrfmiddlewaretoken')[0].value

        return new Promise((resolve, reject) => {// -> HttpResponse
            $.ajax(
              {
              url: '../../liblaas/' + endpoint,
              type: 'post',
              data: JSON.stringify(json_data),
              headers: {
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            },
              dataType: 'text',
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
        let jsonObject = JSON.parse('{"name": "UNH_IOL","description": "University of New Hampshire InterOperability Lab","location": "NH","status": 0}');
        return [new LabBlob(jsonObject)];
    }

    static async getLabFlavors(project) { // -> List<FlavorBlob>
        const response = await this.handleResponse(this.makeRequest(endpoint.FLAVORS, {"project": project}));
        let flavors = [];
        let data = JSON.parse(response)
        if (data) {
            for (const d of data.flavors_list) {
                flavors.push(new FlavorBlob(d))
            }
        } else {
            apiError("flavors")
        }
        return flavors;
    }

    static async getTemplatesForUser() { // -> List<TemplateBlob>
        const response = await this.handleResponse(this.makeRequest(endpoint.TEMPLATES, {}))
        let templates = []
        let data = JSON.parse(response)
        if (data)
        for (const d of data.templates_list) {
            templates.push(new TemplateBlob(d))
        } else {
            apiError("templates")
        }
        return templates;
    }

    static async makeTemplate(templateBlob) { // -> UUID or null
        templateBlob.owner = user; // todo - remove this and handle this in django
        return await this.handleResponse(this.makeRequest(endpoint.MAKE_TEMPLATE, {"template_blob": templateBlob}));
    }

    static async makeBooking(bookingBlob) {
        return await this.handleResponse(this.makeRequest(endpoint.MAKE_BOOKING, {"booking_blob": bookingBlob}));
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
        this.goTo(this.step -1);
    }

    goNext() {
        this.goTo(this.step + 1);
    }

    goTo(step_number) {
        if (step_number < 0) return;
        this.step = step_number
        document.getElementById('workflow-next').removeAttribute('hidden');
        document.getElementById('workflow-prev').removeAttribute('hidden');

        document.getElementById(this.sections[this.step]).scrollIntoView({behavior: 'smooth'});

        if (this.step == 0) {
            document.getElementById('workflow-prev').setAttribute('hidden', '');

        }

        if (this.step == this.sections.length - 1) {
            document.getElementById('workflow-next').setAttribute('hidden', '');
        }
    }

}

function apiError(info) {
    showError("Unable to fetch " + info +". Please try again later or contact support.")
  }

// global variable needed for a scrollintoview bug affecting chrome
let alert_destination = -1;
function showError(message, destination) {
    alert_destination = destination;
    const text = document.getElementById('alert_modal_message');
    text.innerText = message;
    $("#alert_modal").modal('show');
}
