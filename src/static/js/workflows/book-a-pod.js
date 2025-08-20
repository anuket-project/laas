/**
 * book-a-pod.js
 */
class BookingWorkflow extends Workflow {
    constructor(savedBookingBlob) {
        super(["select_template", "cloud_init", "booking_details" , "booking_summary"])


        this.bookingBlob = new BookingBlob({});
        this.userTemplates = null;
        this.images = null;
        this.bookingId = null;
        this.addCollaboratorWidget = new addCollaboratorWidget();
    }

    async startWorkflow() {
        this.userTemplates = await LibLaaSAPI.getTemplatesForUser(dashboard_project)
        this.images =  await LibLaaSAPI.getImages()
        const flavorsList = await LibLaaSAPI.getLabFlavors(dashboard_project)
        this.labFlavors = new Map(); // Map<UUID, FlavorBlob>
        for (const fblob of flavorsList) {
            this.labFlavors.set(fblob.flavor_id, fblob);
        }
        this.setEventListeners();
        workflow.onchangeDays();
        await this.addCollaboratorWidget.init([]);
        
    }

    setEventListeners() {
        
        document.getElementById('ci-file-input').addEventListener('change', this.onUploadCIFile);
        document.getElementById('input_length').addEventListener('input', this.onchangeDays);
        document.getElementById('input_project').addEventListener('input', this.onSelectProject);
        document.getElementById('input_purpose').addEventListener('input', this.onSelectPurpose);
        document.getElementById('input_details').addEventListener('input', this.onAddDetails);


        let templateSelects = document.querySelectorAll(".template-select");
        this.onTemplateSelected = this.onTemplateSelected.bind(this)
        templateSelects.forEach(elem => {
            // Done this way so the function can still access instance variables with this.__ and access the given element without getElementById()
            elem.addEventListener('input', (elem, w=this) => {
                w.onTemplateSelected(elem.target)
            });
        });

    }

    // Update the label for ci-file upload manually since Bootstrap 4 requires JS to update the label text for a file upload
    onUploadCIFile() {
        var file = document.getElementById('ci-file-input').files[0]
        var fileName = file.name;
        var label = document.getElementById('ci-file-label');
        label.textContent = fileName;


        var reader = new FileReader();
        reader.readAsText(file, "UTF-8");
        
        // The reader will never "fail" to read the file because all files can technically be read as text
        reader.onload = function (evt) {
            workflow.bookingBlob.global_cifile = evt.target.result;
        }
        
    }


    onchangeDays() {
        const counter = $("#booking_details_day_counter")
        const input = document.getElementById('input_length');
        var curr_date = new Date();
        curr_date.setDate(Number(curr_date.getDate()) + Number(input.value));
        const options = { month: "long" };
        workflow.bookingBlob.metadata.length = input.value;
        const datetime = `${new Intl.DateTimeFormat("en-US", options).format(curr_date)} ${curr_date.getDate()}, ${curr_date.getFullYear()}`
        counter.children()[0].innerText = `${input.value}`
        counter.children()[1].innerText = `${datetime}`
    }

    onSelectProject() {
        workflow.bookingBlob.metadata.project = this.value;
    }

    onSelectPurpose() {
        workflow.bookingBlob.metadata.purpose = this.value;
    }

    onAddDetails() {
        if (this.value.length > 30) {
            workflow.bookingBlob.metadata.details = this.value;    
        } else {
            workflow.bookingBlob.metadata.details = null;
        }
    }

    onTemplateSelected(elem) {
        let selectedTemplateId = elem.options[elem.selectedIndex].value;

        // Deselect other select field in order to prevent edge case where user only has 1 private template resulting in them being unable to change the template description to that private template after selecting it then a public template  
        let templateSelectors = document.querySelectorAll(".template-select");
        templateSelectors.forEach(e => {
            if (e.selectedIndex != -1 && (e.options[e.options.selectedIndex].value) != selectedTemplateId) {
                e.selectedIndex = -1;
            }
        })


        let template;
        for (template of this.userTemplates) {
            if (template.id == selectedTemplateId) {
                break;
            }
        }
        

        document.getElementById("template-header").textContent = template.pod_name;
        document.getElementById("template-description").textContent = template.pod_desc;


        let isAvailable = GUI.calculateAvailability(template, this.labFlavors) > 0;
        let available_elem = document.getElementById("template-availability");

        available_elem.textContent = isAvailable ? 'Resources Available' : 'Resources Unavailable';
        available_elem.classList.remove("text-success");
        available_elem.classList.remove("text-danger");
        available_elem.classList.add(isAvailable ? 'text-success' : 'text-danger');

        this.bookingBlob.template_id = null;
        if (isAvailable) {
            this.bookingBlob.template_id = template.id
        }


        document.getElementById("ciFile_input").hidden = false;
        document.getElementById("ciFile_disabled-notice").hidden = true;

        for (let host of template.host_list) {
            if (this.images.find((image) => image.image_id === host.image).distro !== "Ubuntu"  ) {

                document.getElementById("ciFile_input").hidden = true;
                document.getElementById("ciFile_disabled-notice").hidden = false;

                break;
            }
        }

    }

    isCompleteBookingInfo() {
        let passed = true
        let message = "success"
        const blob = this.bookingBlob;
        const meta = blob.metadata;

        if (blob.template_id == null) {
            passed = false;
            message = "Please select an available template."
            return [passed, message]
        }

        if (meta.purpose == null || meta.project == null || meta.details == null || meta.details.length < 30 || meta.length == 0) {
            passed = false;
            message = "Please finish adding booking details."
            return [passed, message]
        }
        
        if (!this.addCollaboratorWidget.isValid()) {
            passed = false;
            message = "Please finish adding collaborators. \n\n Please note that a collaborator has not been added unless they appear in the \"Added Collaborators\" list."
            return [passed, message]

        } 

        return[passed, message];
    }


    /** Async / await is more infectious than I thought, so all functions that rely on an API call will need to be async */
    async onclickConfirm() {
        // disable button
        const button = document.getElementById("booking-confirm-button");
        $("html").css("cursor", "wait");
        button.setAttribute('disabled', 'true');
        const complete = this.isCompleteBookingInfo();
        if (!complete[0]) {
            showError(complete[1], -2);
            $("html").css("cursor", "default");
            button.removeAttribute('disabled');
            return;
        }

        this.bookingBlob.allowed_users = this.addCollaboratorWidget.getCollaboratorNames();
        const response = await LibLaaSAPI.makeBooking(this.bookingBlob);
        if (!response) {
            showError("The selected resources for this booking are unavailable at this time. Please select a different resource or try again later.", -1)
            $("html").css("cursor", "default");
            button.removeAttribute('disabled');
            return;
        }
        const r = JSON.parse(response)
        if (r.bookingId) {
            this.bookingId = r.bookingId;
            let msg = "The booking has been successfully created.";
            if (r.warnings.length > 0) {
                msg += "\n\nWarnings:"
            }

            for (const w of r.warnings) {
                msg += `\n${w}\n`
            }

            // Set confirmation modal to have a redirect to the booking's detail 
            let e = document.getElementById("alert-modal-submit");
            e.setAttribute("onclick", "workflow.redirectToDetail()")


            console.log(r.warnings);
            showError(msg, -2);
            $("html").css("cursor", "default");
            return;
        } else {
            if (r.error == true) {
                showError(r.message, -1)
            } else {
                showError("The booking could not be created at this time.", -1)
            }
        }
        $("html").css("cursor", "default");
        button.removeAttribute('disabled');
    }

    redirectToDetail() {
        window.location.href = ("../../booking/detail/" + this.bookingId);
    }
}


/** View class that displays cards and generates HTML 
 * Functions as a namespace, does not hold state
*/
class GUI {

    static calculateAvailability(templateBlob, flavor_map) {
        const local_map = new Map()
  
        // Map flavor uuid to amount in template
        for (const host of templateBlob.host_list) {
            const existing_count = local_map.get(host.flavor)
            if (existing_count) {
                local_map.set(host.flavor, existing_count + 1)
            } else {
                local_map.set(host.flavor, 1)
            }
        }
  
        let lowest_count = Number.POSITIVE_INFINITY;
        for (const [key, val] of local_map) {
            const curr_count =  Math.floor(flavor_map.get(key).available_count / val)
            if (curr_count < lowest_count) {
                lowest_count = curr_count;
            }
        }
  
        return lowest_count;
      }

}