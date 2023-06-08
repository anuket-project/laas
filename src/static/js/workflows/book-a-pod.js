/**
 * book-a-pod.js
 */

const steps = {
    SELECT_TEMPLATE: 0,
    CLOUD_INIT: 1,
    BOOKING_DETAILS: 2,
    ADD_COLLABS: 3,
    BOOKING_SUMMARY: 4
  }

  class BookingWorkflow extends Workflow {
    constructor(savedBookingBlob) {
        super(["select_template", "cloud_init", "booking_details" ,"add_collabs", "booking_summary"])

        // if (savedBookingBlob) {
        //     this.resume_workflow()
        // }

        this.bookingBlob = new BookingBlob({});
        this.userTemplates = null;
    }

    async startWorkflow() {
        this.userTemplates = await LibLaaSAPI.getTemplatesForUser() // List<TemplateBlob>
        GUI.displayTemplates(this.userTemplates);
        GUI.modifyCollabWidget();
        this.setEventListeners();
        document.getElementById(this.sections[0]).scrollIntoView({behavior: 'smooth'});
    }

    setEventListeners() {
        const ci_textarea = document.getElementById('ci-textarea');
        ci_textarea.value = ""
        ci_textarea.addEventListener('focusin', this.onFocusInCIFile);
        ci_textarea.addEventListener('focusout', this.onFocusOutCIFile);
        
        const input_purpose = document.getElementById('input_purpose');
        input_purpose.value = ""
        input_purpose.addEventListener('focusin', this.onFocusInPurpose);
        input_purpose.addEventListener('focusout', this.onFocusOutPurpose)

        const input_project = document.getElementById('input_project');
        input_project.value = ""
        input_project.addEventListener('focusin', this.onFocusInProject);
        input_project.addEventListener('focusout', this.onFocusOutProject);

        const input_length = document.getElementById('input_length');
        input_length.value = 1;
    }

    getTemplateBlobFromId(templateId) {
        for (const t of this.userTemplates) {
            if (t.id == templateId) return t
        }

        return null
    }

    onclickSelectTemplate(templateCard, templateId) {
        this.step = steps.SELECT_TEMPLATE
        const oldHighlight = document.querySelector("#default_templates_list .selected_node")
        if (oldHighlight) {
            GUI.unhighlightCard(oldHighlight)
        }

        GUI.highlightCard(templateCard);
        this.bookingBlob.template_id = templateId;
        GUI.refreshSummaryHosts(this.getTemplateBlobFromId(templateId));
    }

    isValidCIFile(ci_file) {
        // todo
        return true;
    }

    isValidProject(project) {
        let passed = true
        let message = "success"

        if (project == "") {
            passed = false;
            message = "Project field cannot be empty."
            return[passed, message]
        }

        if (!(project.match(/^[a-z0-9~@#$^*()_+=[\]{}|,.?': -]+$/i))) {
            passed = false;
            message = "Project field contains invalid characters"
            return[passed, message]
        }

        return [passed, message]
    }

    isValidPurpose(purpose) {
        let passed = true
        let message = "success"

        if (purpose == "") {
            passed = false;
            message = "Purpose field cannot be empty."
            return[passed, message]
        }

        if (!(purpose.match(/^[a-z0-9~@#$^*()_+=[\]{}|,.?': -]+$/i))) {
            passed = false;
            message = "Purpose field contains invalid characters"
            return[passed, message]
        }

        return [passed, message]
    }

    // Ci FIle
    onFocusOutCIFile() {
        const ci_textarea = document.getElementById('ci-textarea');
        if (workflow.isValidCIFile(ci_textarea.value)) {
            workflow.bookingBlob.global_cifile = ci_textarea.value;
        } else {
            GUI.highlightError(ci_textarea);
        }
    }

    onFocusInCIFile() {
        this.step = steps.CLOUD_INIT
        const ci_textarea = document.getElementById('ci-textarea')
        GUI.unhighlightError(ci_textarea)
    }

    // Purpose
    onFocusOutPurpose() {
        const input = document.getElementById('input_purpose');
        const valid = workflow.isValidPurpose(input.value);
        if (valid[0]) {
            workflow.bookingBlob.metadata.purpose = input.value;
            GUI.refreshSummaryDetails(workflow.bookingBlob.metadata)
        } else {
            GUI.showDetailsError(valid[1])
            GUI.highlightError(input);
        }
    }

    onFocusInPurpose() {
        this.step = steps.BOOKING_DETAILS
        const input = document.getElementById('input_purpose');
        GUI.hideDetailsError()
        GUI.unhighlightError(input)
    }

    // Project
    onFocusOutProject() {
        const input = document.getElementById('input_project');
        const valid = workflow.isValidProject(input.value);
        if (valid[0]) {
            workflow.bookingBlob.metadata.project = input.value;
            GUI.refreshSummaryDetails(workflow.bookingBlob.metadata)
        } else {
            GUI.showDetailsError(valid[1])
            GUI.highlightError(input);
        }
    }

    onFocusInProject() {
        this.step = steps.BOOKING_DETAILS
        const input = document.getElementById('input_project');
        GUI.hideDetailsError()
        GUI.unhighlightError(input)
    }

    onchangeDays() {
        this.step = steps.BOOKING_DETAILS
        const counter = document.getElementById("booking_details_day_counter")
        const input = document.getElementById('input_length')
        workflow.bookingBlob.metadata.length = input.value
        GUI.refreshSummaryDetails(workflow.bookingBlob.metadata)
        counter.innerText = "Days: " + input.value
    }

    add_collaborator(username) {
        this.step = steps.ADD_COLLABS;

        for (const c of this.bookingBlob.allowed_users) {
            if (c == username) {
                return;
            }
        }

        this.bookingBlob.allowed_users.push(username)
        GUI.refreshSummaryCollabs(this.bookingBlob.allowed_users)
    }

    remove_collaborator(username) {
        // Removes collab from collaborators list and updates summary
        this.step = steps.ADD_COLLABS

        const temp = [];

        for (const c of this.bookingBlob.allowed_users) {
            if (c != username) {
                temp.push(c);
            }
        }

        this.bookingBlob.allowed_users = temp;
        GUI.refreshSummaryCollabs(this.bookingBlob.allowed_users)
    }

    isCompleteBookingInfo() {
        let passed = true
        let message = "success"
        let section = steps.BOOKING_SUMMARY

        const blob = this.bookingBlob;
        const meta = blob.metadata;

        if (blob.template_id == null) {
            passed = false;
            message = "Please select a template."
            section = steps.SELECT_TEMPLATE
            return [passed, message, section]
        }

        if (meta.purpose == null || meta.project == null || meta.length == 0) {
            passed = false
            message = "Please finish adding booking details."
            section = steps.BOOKING_DETAILS
            return [passed, message, section]
        }

        return[passed, message, section];
    }

    onclickCancel() {
        if (confirm("Are you sure you wish to discard this booking?")) {
            location.reload();
        }
    }

    /** Async / await is more infectious than I thought, so all functions that rely on an API call will need to be async */
    async onclickConfirm() {
        const complete = this.isCompleteBookingInfo();
        if (!complete[0]) {
            alert(complete[1]);
            this.step = complete[2]
            document.getElementById(this.sections[complete[2]]).scrollIntoView({behavior: 'smooth'});
            return
        }
        if (confirm("Are you sure you would like to create this booking?")) {
            const response = await LibLaaSAPI.makeBooking(this.bookingBlob);
            if (response.bookingId) {
                alert("The booking has been successfully created.")
                window.location.href = "../../";
            } else {
                alert("The booking could not be created at this time.")
            }
        }
    }
    


  }


/** View class that displays cards and generates HTML 
 * Functions as a namespace, does not hold state
*/
class GUI {

    static highlightCard(card) {
        card.classList.add('selected_node');
    }
  
    static unhighlightCard(card) {
    card.classList.remove('selected_node');
    }

    static highlightError(element) {
        element.classList.add('invalid_field');
    }
  
    static unhighlightError(element) {
    element.classList.remove("invalid_field");
    }

    /** Takes a list of templateBlobs and creates a selectable card for each of them */
    static displayTemplates(templates) {
        const templates_list = document.getElementById("default_templates_list");

        for (const t of templates) {
            const newCard = this.makeTemplateCard(t);
            templates_list.appendChild(newCard);
        }
    }

    static makeTemplateCard(templateBlob) {
        const col = document.createElement('div');
        col.classList.add('col-3', 'my-1');
        col.innerHTML=  `
          <div class="card">
            <div class="card-header">
                <p class="h5 font-weight-bold mt-2">` + templateBlob.pod_name + `</p>
            </div>
            <div class="card-body">
                <p class="grid-item-description">` + templateBlob.pod_desc +`</p>
            </div>
            <div class="card-footer">
                <button type="button" class="btn btn-success grid-item-select-btn w-100 stretched-link" 
                onclick="workflow.onclickSelectTemplate(this.parentNode.parentNode, '` + templateBlob.id +`')">Select</button>
            </div>
          </div>
        `
        return col;
    }

    /** Removes default styling applied by django */
    static modifyCollabWidget() {
        document.getElementsByTagName('label')[0].setAttribute('hidden', '');
        document.getElementById('addable_limit').setAttribute('hidden', '');
        document.getElementById('added_number').setAttribute('hidden', '');
        const user_field = document.getElementById('user_field');
        user_field.classList.add('border-top-0');
        document.querySelector('.form-group').classList.add('mb-0');

        const added_list = document.getElementById('added_list');
        added_list.remove();
        document.getElementById('search_select_outer').appendChild(added_list);
    }

    static showDetailsError(message) {
        document.getElementById("booking_details_error").innerText = message;
    }

    static hideDetailsError() {
        document.getElementById("booking_details_error").innerText = '';
    }

    static refreshSummaryDetails(bookingMetaData) {
        const ul = document.getElementById("booking_summary_booking_details")
        ul.innerHTML = '';

        if (bookingMetaData.project) {
            const project_li = document.createElement('li');
            project_li.innerText = 'Project: ' + bookingMetaData.project;
            ul.appendChild(project_li);
        }

        if (bookingMetaData.purpose) {
            const project_li = document.createElement('li');
            project_li.innerText = 'Purpose: ' + bookingMetaData.purpose;
            ul.appendChild(project_li);
        }

        if (bookingMetaData.length) {
            const project_li = document.createElement('li');
            project_li.innerText = 'Length: ' + bookingMetaData.length + ' days';
            ul.appendChild(project_li);
        }
    }

    static refreshSummaryCollabs(collaborators) {
        const collabs_ul = document.getElementById('booking_summary_collaborators');
        collabs_ul.innerHTML = '';
        for (const u of collaborators) {
            const collabs_li = document.createElement('li');
            collabs_li.innerText = u
            collabs_ul.appendChild(collabs_li);
        }
    }

    static refreshSummaryHosts(templateBlob) {
        const hosts_ul = document.getElementById('booking_summary_hosts');
        hosts_ul.innerHTML = '';
        for (const h of templateBlob.host_list) {
            const hosts_li = document.createElement('li');
            hosts_li.innerText = h.hostname;
            hosts_ul.appendChild(hosts_li);
        }
    }
}


 // Search widget for django forms (taken from dashboard.js and slightly modified)
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
            result_entry.href = "#";
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
            deleteButton.href = "#";
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