/**
 * book-a-pod.js
 */
class BookingWorkflow extends Workflow {
    constructor(savedBookingBlob) {
        super(["select_template", "cloud_init", "booking_details" , "booking_summary"])


        this.bookingBlob = new BookingBlob({});
        this.userTemplates = null;
    }

    async startWorkflow() {
        this.userTemplates = await LibLaaSAPI.getTemplatesForUser(dashboard_project)
        const flavorsList = await LibLaaSAPI.getLabFlavors(dashboard_project)
        this.labFlavors = new Map(); // Map<UUID, FlavorBlob>
        for (const fblob of flavorsList) {
            this.labFlavors.set(fblob.flavor_id, fblob);
        }
        this.setEventListeners();
        GUI.modifyCollabWidget();
        workflow.onchangeDays();
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

    }

    add_collaborator(username) {
        for (const c of this.bookingBlob.allowed_users) {
            if (c == username) {
                return;
            }
        }

        this.bookingBlob.allowed_users.push(username)
        // GUI.refreshSummaryCollabs(this.bookingBlob.allowed_users)
    }

    remove_collaborator(username) {
        // Removes collab from collaborators list and updates summary

        const temp = [];

        for (const c of this.bookingBlob.allowed_users) {
            if (c != username) {
                temp.push(c);
            }
        }

        this.bookingBlob.allowed_users = temp;
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
            passed = false
            message = "Please finish adding booking details."
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

            console.log(r.warnings);
            showError(msg, -2);
            //window.location.href = ("../../booking/detail/" + this.bookingId);
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


    /** Removes default styling applied by django */
      // Trimmed by adding args to django template function
    static modifyCollabWidget() {
        document.getElementById('addable_limit').setAttribute('hidden', '');
        document.getElementById('added_number').setAttribute('hidden', '');
        document.querySelector('.form-group').classList.add('mb-0');

        const added_list = document.getElementById('added_list');
        added_list.remove();
        document.getElementById('search_select_outer').appendChild(added_list);
    }

    
}


 // Search widget for django forms (taken from dashboard.js and slightly modified)
    // For Add Collaborators section
 class SearchableSelectMultipleWidget {
    constructor(format_vars, field_dataset, field_initial) {
        this.format_vars = format_vars;
        this.items = field_dataset;
        this.initial = field_initial;

        this.expanded_name_trie = {"isComplete": false};
        this.small_name_trie = {"isComplete": false};
        this.string_trie = {"isComplete": false};

        this.added_items = new Set();

        for( let e of ["show_from_noentry", "show_x_results", "results_scrollable", "selectable_limit", "placeholder"] )
        {
            this[e] = format_vars[e];
        }

        this.search_field_init();

        if( this.show_from_noentry )
        {
            this.search("");
        }
    }

    disable() {
        const textfield = document.getElementById("user_field");
        const drop = document.getElementById("drop_results");

        textfield.disabled = "True";
        drop.style.display = "none";

        const btns = document.getElementsByClassName("btn-remove");
        for( const btn of btns )
        {
            btn.classList.add("disabled");
            btn.onclick = "";
        }
    }

    search_field_init() {
        this.build_all_tries(this.items);

        for( const elem of this.initial )
        {
            this.select_item(elem);
        }
        if(this.initial.length == 1)
        {
            this.search(this.items[this.initial[0]]["small_name"]);
            document.getElementById("user_field").value = this.items[this.initial[0]]["small_name"];
        }
    }

    build_all_tries(dict)
    {
        for( const key in dict )
        {
            this.add_item(dict[key]);
        }
    }

    add_item(item)
    {
        const id = item['id'];
        this.add_to_tree(item['expanded_name'], id, this.expanded_name_trie);
        this.add_to_tree(item['small_name'], id, this.small_name_trie);
        this.add_to_tree(item['string'], id, this.string_trie);
    }

    add_to_tree(str, id, trie)
    {
        let inner_trie = trie;
        while( str )
        {
            if( !inner_trie[str.charAt(0)] )
            {
                var new_trie = {};
                inner_trie[str.charAt(0)] = new_trie;
            }
            else
            {
                var new_trie = inner_trie[str.charAt(0)];
            }

            if( str.length == 1 )
            {
                new_trie.isComplete = true;
                if( !new_trie.ids )
                {
                    new_trie.ids = [];
                }
                new_trie.ids.push(id);
            }
            inner_trie = new_trie;
            str = str.substring(1);
        }
    }

    search(input)
    {
        if( input.length == 0 && !this.show_from_noentry){
            this.dropdown([]);
            return;
        }
        else if( input.length == 0 && this.show_from_noentry)
        {
            this.dropdown(this.items); //show all items
        }
        else
        {
            const trees = []
            const tr1 = this.getSubtree(input, this.expanded_name_trie);
            trees.push(tr1);
            const tr2 = this.getSubtree(input, this.small_name_trie);
            trees.push(tr2);
            const tr3 = this.getSubtree(input, this.string_trie);
            trees.push(tr3);
            const results = this.collate(trees);
            this.dropdown(results);
        }
    }

    getSubtree(input, given_trie)
    {
        /*
        recursive function to return the trie accessed at input
        */

        if( input.length == 0 ){
            return given_trie;
        }

        else{
            const substr = input.substring(0, input.length - 1);
            const last_char = input.charAt(input.length-1);
            const subtrie = this.getSubtree(substr, given_trie);

            if( !subtrie ) //substr not in the trie
            {
                return {};
            }

            const indexed_trie = subtrie[last_char];
            return indexed_trie;
        }
    }

    serialize(trie)
    {
        /*
        takes in a trie and returns a list of its item id's
        */
        let itemIDs = [];
        if ( !trie )
        {
            return itemIDs; //empty, base case
        }
        for( const key in trie )
        {
            if(key.length > 1)
            {
                continue;
            }
            itemIDs = itemIDs.concat(this.serialize(trie[key]));
        }
        if ( trie.isComplete )
        {
            itemIDs.push(...trie.ids);
        }

        return itemIDs;
    }

    collate(trees)
    {
        /*
        takes a list of tries
        returns a list of ids of objects that are available
        */
        const results = [];
        for( const tree of trees )
        {
            const available_IDs = this.serialize(tree);

            for( const itemID of available_IDs ) {
                results[itemID] = this.items[itemID];
            }
        }
        return results;
    }

    generate_element_text(obj)
    {
        const content_strings = [obj.expanded_name, obj.small_name, obj.string].filter(x => Boolean(x));
        const result = content_strings.shift();
        if( result == null || content_strings.length < 1) {
            return result;
        } else {
            return result + " (" + content_strings.join(", ") + ")";
        }
    }

    dropdown(ids)
    {
        /*
        takes in a mapping of ids to objects in items
        and displays them in the dropdown
        */
        const drop = document.getElementById("drop_results");
        while(drop.firstChild)
        {
            drop.removeChild(drop.firstChild);
        }

        for( const id in ids )
        {
            const obj = this.items[id];
            const result_text = this.generate_element_text(obj);
            const result_entry = document.createElement("a");
            //result_entry.href = "#";
            result_entry.innerText = result_text;
            result_entry.title = result_text;
            result_entry.classList.add("list-group-item", "list-group-item-action", "overflow-ellipsis", "flex-shrink-0");
            result_entry.onclick = function() { searchable_select_multiple_widget.select_item(obj.id); };
            const tooltip = document.createElement("span");
            const tooltiptext = document.createTextNode(result_text);
            tooltip.appendChild(tooltiptext);
            tooltip.classList.add("d-none");
            result_entry.appendChild(tooltip);
            drop.appendChild(result_entry);
        }

        const scroll_restrictor = document.getElementById("scroll_restrictor");

        if( !drop.firstChild )
        {
            scroll_restrictor.style.visibility = 'hidden';
        }
        else
        {
            scroll_restrictor.style.visibility = 'inherit';
        }
    }

    select_item(item_id)
    {
        if( (this.selectable_limit > -1 && this.added_items.size < this.selectable_limit) || this.selectable_limit < 0 )
        {
            this.added_items.add(item_id);
        }
        this.update_selected_list();
        // clear search bar contents
        document.getElementById("user_field").value = "";
        document.getElementById("user_field").focus();
        this.search("");

        const item = this.items[item_id];
        const element_entry_text = this.generate_element_text(item);
        const username = item.small_name;
        workflow.add_collaborator(username, element_entry_text);
    }

    remove_item(item_id)
    {
        this.added_items.delete(item_id); // delete from set

        const item = this.items[item_id];
        workflow.remove_collaborator(item.small_name);

        this.update_selected_list();
        document.getElementById("user_field").focus();
    }

    /* This looks like alot of it can be removed */
    update_selected_list()
    {
        document.getElementById("added_number").innerText = this.added_items.size;
        const selector = document.getElementById('selector');
        selector.value = JSON.stringify([...this.added_items]);
        const added_list = document.getElementById('added_list');

        while(selector.firstChild)
        {
            selector.removeChild(selector.firstChild);
        }
        while(added_list.firstChild)
        {
            added_list.removeChild(added_list.firstChild);
        }

        const list_html = document.createElement("div");
        list_html.classList.add("list-group");

        for( const item_id of this.added_items )
        {
            const times = document.createElement("li");
            times.classList.add("fas", "fa-times");

            const deleteButton = document.createElement("a");
            //deleteButton.href = "#";
            deleteButton.innerHTML = "<i class='fas fa-times'></i>"
            deleteButton.setAttribute("onclick", `searchable_select_multiple_widget.remove_item(${item_id});`); 
            deleteButton.classList.add("btn");
            const deleteColumn = document.createElement("div");
            deleteColumn.classList.add("col-auto");
            deleteColumn.append(deleteButton);

            const item = this.items[item_id];
            const element_entry_text = this.generate_element_text(item);
            const textColumn = document.createElement("div");
            textColumn.classList.add("col", "overflow-ellipsis");
            textColumn.innerText = element_entry_text;
            textColumn.title = element_entry_text;
            textColumn.id = `coldel-${item_id}`; // Needed for book a pod

            const itemRow = document.createElement("div");
            itemRow.classList.add("list-group-item", "d-flex", "p-0", "align-items-center", "my-2", "border");
            itemRow.append(textColumn, deleteColumn);

            list_html.append(itemRow);
        }
        added_list.innerHTML = list_html.innerHTML;
    }
}