class MultipleSelectFilterWidget {

    constructor(neighbors, items, initial) {
        this.inputs = [];
        this.graph_neighbors = neighbors;
        this.filter_items = items;
        this.result = {};
        this.dropdown_count = 0;

        for(let nodeId in this.filter_items) {
            const node = this.filter_items[nodeId];
            this.result[node.class] = {}
        }

        this.make_selection(initial);
    }

    make_selection( initial_data ){
        if(!initial_data || jQuery.isEmptyObject(initial_data))
            return;
        for(let item_class in initial_data) {
            const selected_items = initial_data[item_class];
            for( let node_id in selected_items ){
                const node = this.filter_items[node_id];
                const selection_data = selected_items[node_id]
                if( selection_data.selected ) {
                    this.select(node);
                    this.markAndSweep(node);
                    this.updateResult(node);
                }
                if(node['multiple']){
                    this.make_multiple_selection(node, selection_data);
                }
            }
        }
    }

    make_multiple_selection(node, selection_data){
        const prepop_data = selection_data.values;
        for(let k in prepop_data){
            const div = this.add_item_prepopulate(node, prepop_data[k]);
            this.updateObjectResult(node, div.id, prepop_data[k]);
        }
    }

    markAndSweep(root){
        for(let i in this.filter_items) {
            const node = this.filter_items[i];
            node['marked'] = true; //mark all nodes
        }

        const toCheck = [root];
        while(toCheck.length > 0){
            const node = toCheck.pop();
            if(!node['marked']) {
                continue; //already visited, just continue
            }
            node['marked'] = false; //mark as visited
            if(node['follow'] || node == root){ //add neighbors if we want to follow this node
                const neighbors = this.graph_neighbors[node.id];
                for(let neighId of neighbors) {
                    const neighbor = this.filter_items[neighId];
                    toCheck.push(neighbor);
                }
            }
        }

        //now remove all nodes still marked
        for(let i in this.filter_items){
            const node = this.filter_items[i];
            if(node['marked']){
                this.disable_node(node);
            }
        }
    }

    process(node) {
        if(node['selected']) {
            this.markAndSweep(node);
        }
        else {  //TODO: make this not dumb
            const selected = []
            //remember the currently selected, then reset everything and reselect one at a time
            for(let nodeId in this.filter_items) {
                node = this.filter_items[nodeId];
                if(node['selected']) {
                    selected.push(node);
                }
                this.clear(node);
            }
            for(let node of selected) {
                this.select(node);
                this.markAndSweep(selected[i]);
            }
        }
    }

    select(node) {
        const elem = document.getElementById(node['id']);
        node['selected'] = true;
        elem.classList.remove('disabled_node', 'cleared_node');
        elem.classList.add('selected_node');
    }

    clear(node) {
        const elem = document.getElementById(node['id']);
        node['selected'] = false;
        node['selectable'] = true;
        elem.classList.add('cleared_node')
        elem.classList.remove('disabled_node', 'selected_node');
    }

    disable_node(node) {
        const elem = document.getElementById(node['id']);
        node['selected'] = false;
        node['selectable'] = false;
        elem.classList.remove('cleared_node', 'selected_node');
        elem.classList.add('disabled_node');
    }

    processClick(id){
        const node = this.filter_items[id];
        if(!node['selectable'])
            return;

        if(node['multiple']){
            return this.processClickMultiple(node);
        } else {
            return this.processClickSingle(node);
        }
    }

    processClickSingle(node){
        node['selected'] = !node['selected']; //toggle on click
        if(node['selected']) {
            this.select(node);
        } else {
            this.clear(node);
        }
        this.process(node);
        this.updateResult(node);
    }

    processClickMultiple(node){
        this.select(node);
        const div = this.add_item_prepopulate(node, false);
        this.process(node);
        this.updateObjectResult(node, div.id, "");
    }

    restrictchars(input){
        if( input.validity.patternMismatch ){
            input.setCustomValidity("Only alphanumeric characters (a-z, A-Z, 0-9), underscore(_), and hyphen (-) are allowed");
            input.reportValidity();
        }
        input.value = input.value.replace(/([^A-Za-z0-9-_.])+/g, "");
        this.checkunique(input);
    }

    checkunique(tocheck){ //TODO: use set
        const val = tocheck.value;
        for( let input of this.inputs ){
            if( input.value == val && input != tocheck){
                tocheck.setCustomValidity("All hostnames must be unique");
                tocheck.reportValidity();
                return;
            }
        }
        tocheck.setCustomValidity("");
    }

    make_remove_button(div, node){
        const button = document.createElement("BUTTON");
        button.type = "button";
        button.appendChild(document.createTextNode("Remove"));
        button.classList.add("btn", "btn-danger");
        const that = this;
        button.onclick = function(){ that.remove_dropdown(div.id, node.id); }
        return button;
    }

    make_input(div, node, prepopulate){
        const input = document.createElement("INPUT");
        input.type = node.form.type;
        input.name = node.id + node.form.name
        input.pattern = "(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})";
        input.title = "Only alphanumeric characters (a-z, A-Z, 0-9), underscore(_), and hyphen (-) are allowed"
        input.placeholder = node.form.placeholder;
        this.inputs.push(input);
        const that = this;
        input.onchange = function() { that.updateObjectResult(node, div.id, input.value); that.restrictchars(this); };
        input.oninput = function() { that.restrictchars(this); };
        if(prepopulate)
            input.value = prepopulate;
        return input;
    }

    add_item_prepopulate(node, prepopulate){
        const div = document.createElement("DIV");
        div.id = "dropdown_" + this.dropdown_count;
        div.classList.add("dropdown_item");
        this.dropdown_count++;
        const label = document.createElement("H5")
        label.appendChild(document.createTextNode(node['name']))
        div.appendChild(label);
        div.appendChild(this.make_input(div, node, prepopulate));
        div.appendChild(this.make_remove_button(div, node));
        document.getElementById("dropdown_wrapper").appendChild(div);
        return div;
    }

    remove_dropdown(div_id, node_id){
        const div = document.getElementById(div_id);
        const node = this.filter_items[node_id]
        const parent = div.parentNode;
        div.parentNode.removeChild(div);
        delete this.result[node.class][node.id]['values'][div.id];

        //checks if we have removed last item in class
        if(jQuery.isEmptyObject(this.result[node.class][node.id]['values'])){
            delete this.result[node.class][node.id];
            this.clear(node);
        }
    }

    updateResult(node){
        if(!node['multiple']){
            this.result[node.class][node.id] = {selected: node.selected, id: node.model_id}
            if(!node.selected)
                delete this.result[node.class][node.id];
        }
    }

    updateObjectResult(node, childKey, childValue){
        if(!this.result[node.class][node.id])
            this.result[node.class][node.id] = {selected: true, id: node.model_id, values: {}}

        this.result[node.class][node.id]['values'][childKey] = childValue;
    }

    finish(){
        document.getElementById("filter_field").value = JSON.stringify(this.result);
    }
}
