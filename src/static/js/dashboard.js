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
                this.markAndSweep(node);
            }
        }
    }

    select(node) {
        const elem = document.getElementById(node['id']);
        node['selected'] = true;
        elem.classList.remove('bg-white', 'not-allowed', 'bg-light');
        elem.classList.add('selected_node');
    }

    clear(node) {
        const elem = document.getElementById(node['id']);
        node['selected'] = false;
        node['selectable'] = true;
        elem.classList.add('bg-white')
        elem.classList.remove('not-allowed', 'bg-light', 'selected_node');
    }

    disable_node(node) {
        const elem = document.getElementById(node['id']);
        node['selected'] = false;
        node['selectable'] = false;
        elem.classList.remove('bg-white', 'selected_node');
        elem.classList.add('not-allowed', 'bg-light');
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
        button.classList.add("btn", "btn-danger", "d-inline-block");
        const that = this;
        button.onclick = function(){ that.remove_dropdown(div.id, node.id); }
        return button;
    }

    make_input(div, node, prepopulate){
        const input = document.createElement("INPUT");
        input.type = node.form.type;
        input.name = node.id + node.form.name
        input.classList.add("form-control", "w-auto", "d-inline-block");
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
        div.classList.add("list-group-item");
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

class NetworkStep {
    constructor(debug, xml, hosts, added_hosts, removed_host_ids, graphContainer, overviewContainer, toolbarContainer){
        if(!this.check_support())
            return;

        this.currentWindow = null;
        this.netCount = 0;
        this.netColors = ['red', 'blue', 'purple', 'green', 'orange', '#8CCDF5', '#1E9BAC'];
        this.hostCount = 0;
        this.lastHostBottom = 100;
        this.networks = new Set();
        this.has_public_net = false;
        this.debug = debug;
        this.editor = new mxEditor();
        this.graph = this.editor.graph;

        this.editor.setGraphContainer(graphContainer);
        this.doGlobalConfig();
        this.prefill(xml, hosts, added_hosts, removed_host_ids);
        this.addToolbarButton(this.editor, toolbarContainer, 'zoomIn', '', "/static/img/mxgraph/zoom_in.png", true);
        this.addToolbarButton(this.editor, toolbarContainer, 'zoomOut', '', "/static/img/mxgraph/zoom_out.png", true);

        if(this.debug){
            this.editor.addAction('printXML', function(editor, cell) {
                mxLog.write(this.encodeGraph());
                mxLog.show();
            }.bind(this));
            this.addToolbarButton(this.editor, toolbarContainer, 'printXML', '', '/static/img/mxgraph/fit_to_size.png', true);
        }

        new mxOutline(this.graph, overviewContainer);
        //sets the edge color to be the same as the network
        this.graph.addListener(mxEvent.CELL_CONNECTED, function(sender, event) {this.cellConnectionHandler(sender, event)}.bind(this));
        //hooks up double click functionality
        this.graph.dblClick = function(evt, cell) {this.doubleClickHandler(evt, cell);}.bind(this);

        if(!this.has_public_net){
            this.addPublicNetwork();
        }
    }

    check_support(){
        if (!mxClient.isBrowserSupported()) {
            mxUtils.error('Browser is not supported', 200, false);
            return false;
        }
        return true;
    }

    prefill(xml, hosts, added_hosts, removed_host_ids){
        //populate existing data
        if(xml){
            this.restoreFromXml(xml, this.editor);
        } else if(hosts){
            for(const host of hosts)
                this.makeHost(host);
        }

        //apply any changes
        if(added_hosts){
            for(const host of added_hosts)
                this.makeHost(host);
            this.updateHosts([]); //TODO: why?
        }
        this.updateHosts(removed_host_ids);
    }

    cellConnectionHandler(sender, event){
        const edge = event.getProperty('edge');
        const terminal = event.getProperty('terminal')
        const source = event.getProperty('source');
        if(this.checkAllowed(edge, terminal, source)) {
            this.colorEdge(edge, terminal, source);
            this.alertVlan(edge, terminal, source);
        }
    }

    doubleClickHandler(evt, cell) {
        if( cell != null ){
            if( cell.getParent() != null && cell.getParent().getId().indexOf("network") > -1) {
                cell = cell.getParent();
            }
            if( cell.isEdge() || cell.getId().indexOf("network") > -1 ) {
                this.createDeleteDialog(cell.getId());
            }
            else {
                this.showDetailWindow(cell);
           }
        }
    }

    alertVlan(edge, terminal, source) {
        if( terminal == null || edge.getTerminal(!source) == null) {
            return;
        }
        const form = document.createElement("form");
        const tagged = document.createElement("input");
        tagged.type = "radio";
        tagged.name = "tagged";
        tagged.value = "True";
        form.appendChild(tagged);
        form.appendChild(document.createTextNode(" Tagged"));
        form.appendChild(document.createElement("br"));

        const untagged = document.createElement("input");
        untagged.type = "radio";
        untagged.name = "tagged";
        untagged.value = "False";
        form.appendChild(untagged);
        form.appendChild(document.createTextNode(" Untagged"));
        form.appendChild(document.createElement("br"));

        const yes_button = document.createElement("button");
        yes_button.onclick = function() {this.parseVlanWindow(edge.getId());}.bind(this);
        yes_button.appendChild(document.createTextNode("Okay"));

        const cancel_button = document.createElement("button");
        cancel_button.onclick = function() {this.deleteVlanWindow(edge.getId());}.bind(this);
        cancel_button.appendChild(document.createTextNode("Cancel"));

        const error_div = document.createElement("div");
        error_div.id = "current_window_errors";
        form.appendChild(error_div);

        const content = document.createElement('div');
        content.appendChild(form);
        content.appendChild(yes_button);
        content.appendChild(cancel_button);
        this.showWindow("Vlan Selection", content, 200, 200);
    }

    createDeleteDialog(id) {
        const content = document.createElement('div');
        const remove_button = document.createElement("button");
        remove_button.style.width = '46%';
        remove_button.onclick = function() { this.deleteCell(id);}.bind(this);
        remove_button.appendChild(document.createTextNode("Remove"));
        const cancel_button = document.createElement("button");
        cancel_button.style.width = '46%';
        cancel_button.onclick = function() { this.closeWindow();}.bind(this);
        cancel_button.appendChild(document.createTextNode("Cancel"));

        content.appendChild(remove_button);
        content.appendChild(cancel_button);
        this.showWindow('Do you want to delete this network?', content, 200, 62);
    }

    checkAllowed(edge, terminal, source) {
        //check if other terminal is null, and that they are different
        const otherTerminal = edge.getTerminal(!source);
        if(terminal != null && otherTerminal != null) {
            if( terminal.getParent().getId().split('_')[0] == //'host' or 'network'
                otherTerminal.getParent().getId().split('_')[0] ) {
                //not allowed
                this.graph.removeCells([edge]);
                return false;
            }
        }
        return true;
    }

    colorEdge(edge, terminal, source) {
        if(terminal.getParent().getId().indexOf('network') >= 0) {
            const styles = terminal.getParent().getStyle().split(';');
            let color = 'black';
            for(let style of styles){
                const kvp = style.split('=');
                if(kvp[0] == "fillColor"){
                    color = kvp[1];
                }
            }
            edge.setStyle('strokeColor=' + color);
        }
    }

    showDetailWindow(cell) {
        const info = JSON.parse(cell.getValue());
        const content = document.createElement("div");
        const pre_tag = document.createElement("pre");
        pre_tag.appendChild(document.createTextNode("Name: " + info.name + "\nDescription:\n" + info.description));
        const ok_button = document.createElement("button");
        ok_button.onclick = function() { this.closeWindow();};
        content.appendChild(pre_tag);
        content.appendChild(ok_button);
        this.showWindow('Details', content, 400, 400);
    }

    restoreFromXml(xml, editor) {
        const doc = mxUtils.parseXml(xml);
        const node = doc.documentElement;
        editor.readGraphModel(node);

        //Iterate over all children, and parse the networks to add them to the sidebar
        for( const cell of this.graph.getModel().getChildren(this.graph.getDefaultParent())) {
            if(cell.getId().indexOf("network") > -1) {
                const info = JSON.parse(cell.getValue());
                const name = info['name'];
                this.networks.add(name);
                const styles = cell.getStyle().split(";");
                let color = null;
                for(const style of styles){
                    const kvp = style.split('=');
                    if(kvp[0] == "fillColor") {
                        color = kvp[1];
                        break;
                    }
                }
                if(info.public){
                    this.has_public_net = true;
                }
                this.netCount++;
                this.makeSidebarNetwork(name, color, cell.getId());
            }
        }
    }

    deleteCell(cellId) {
        var cell = this.graph.getModel().getCell(cellId);
        if( cellId.indexOf("network") > -1 ) {
            let elem = document.getElementById(cellId);
            elem.parentElement.removeChild(elem);
        }
        this.graph.removeCells([cell]);
        this.currentWindow.destroy();
    }

    newNetworkWindow() {
        const input = document.createElement("input");
        input.type = "text";
        input.name = "net_name";
        input.maxlength = 100;
        input.id = "net_name_input";
        input.style.margin = "5px";

        const yes_button = document.createElement("button");
        yes_button.onclick = function() {this.parseNetworkWindow();}.bind(this);
        yes_button.appendChild(document.createTextNode("Okay"));

        const cancel_button = document.createElement("button");
        cancel_button.onclick = function() {this.closeWindow();}.bind(this);
        cancel_button.appendChild(document.createTextNode("Cancel"));

        const error_div = document.createElement("div");
        error_div.id = "current_window_errors";

        const content = document.createElement("div");
        content.appendChild(document.createTextNode("Name: "));
        content.appendChild(input);
        content.appendChild(document.createElement("br"));
        content.appendChild(yes_button);
        content.appendChild(cancel_button);
        content.appendChild(document.createElement("br"));
        content.appendChild(error_div);

        this.showWindow("Network Creation", content, 300, 300);
    }

    parseNetworkWindow() {
        const net_name = document.getElementById("net_name_input").value
        const error_div = document.getElementById("current_window_errors");
        if( this.networks.has(net_name) ){
            error_div.innerHTML = "All network names must be unique";
            return;
        }
        this.addNetwork(net_name);
        this.currentWindow.destroy();
    }

    addToolbarButton(editor, toolbar, action, label, image, isTransparent) {
        const button = document.createElement('button');
        button.style.fontSize = '10';
        if (image != null) {
            const img = document.createElement('img');
            img.setAttribute('src', image);
            img.style.width = '16px';
            img.style.height = '16px';
            img.style.verticalAlign = 'middle';
            img.style.marginRight = '2px';
            button.appendChild(img);
        }
        if (isTransparent) {
            button.style.background = 'transparent';
            button.style.color = '#FFFFFF';
            button.style.border = 'none';
        }
        mxEvent.addListener(button, 'click', function(evt) {
            editor.execute(action);
        });
        mxUtils.write(button, label);
        toolbar.appendChild(button);
    };

    encodeGraph() {
        const encoder = new mxCodec();
        const xml = encoder.encode(this.graph.getModel());
        return mxUtils.getXml(xml);
    }

    doGlobalConfig() {
        //general graph stuff
        this.graph.setMultigraph(false);
        this.graph.setCellsSelectable(false);
        this.graph.setCellsMovable(false);

        //testing
        this.graph.vertexLabelIsMovable = true;

        //edge behavior
        this.graph.setConnectable(true);
        this.graph.setAllowDanglingEdges(false);
        mxEdgeHandler.prototype.snapToTerminals = true;
        mxConstants.MIN_HOTSPOT_SIZE = 16;
        mxConstants.DEFAULT_HOTSPOT = 1;
        //edge 'style' (still affects behavior greatly)
        const style = this.graph.getStylesheet().getDefaultEdgeStyle();
        style[mxConstants.STYLE_EDGE] = mxConstants.EDGESTYLE_ELBOW;
        style[mxConstants.STYLE_ENDARROW] = mxConstants.NONE;
        style[mxConstants.STYLE_ROUNDED] = true;
        style[mxConstants.STYLE_FONTCOLOR] = 'black';
        style[mxConstants.STYLE_STROKECOLOR] = 'red';
        style[mxConstants.STYLE_LABEL_BACKGROUNDCOLOR] = '#FFFFFF';
        style[mxConstants.STYLE_STROKEWIDTH] = '3';
        style[mxConstants.STYLE_ROUNDED] = true;
        style[mxConstants.STYLE_EDGE] = mxEdgeStyle.EntityRelation;

        const hostStyle = this.graph.getStylesheet().getDefaultVertexStyle();
        hostStyle[mxConstants.STYLE_ROUNDED] = 1;

        this.graph.convertValueToString = function(cell) {
            try{
                //changes value for edges with xml value
                if(cell.isEdge()) {
                    if(JSON.parse(cell.getValue())["tagged"]) {
                        return "tagged";
                    }
                    return "untagged";
                }
                else{
                    return JSON.parse(cell.getValue())['name'];
                }
            }
            catch(e){
                return cell.getValue();
            }
        };
    }

    showWindow(title, content, width, height) {
        //create transparent black background
        const background = document.createElement('div');
        background.style.position = 'absolute';
        background.style.left = '0px';
        background.style.top = '0px';
        background.style.right = '0px';
        background.style.bottom = '0px';
        background.style.background = 'black';
        mxUtils.setOpacity(background, 50);
        document.body.appendChild(background);

        const x = Math.max(0, document.body.scrollWidth/2-width/2);
        const y = Math.max(10, (document.body.scrollHeight ||
                    document.documentElement.scrollHeight)/2-height*2/3);

        const wnd = new mxWindow(title, content, x, y, width, height, false, true);
        wnd.setClosable(false);

        wnd.addListener(mxEvent.DESTROY, function(evt) {
            this.graph.setEnabled(true);
            mxEffects.fadeOut(background, 50, true, 10, 30, true);
        }.bind(this));
        this.currentWindow = wnd;

        this.graph.setEnabled(false);
        this.currentWindow.setVisible(true);
    };

    closeWindow() {
        //allows the current window to be destroyed
        this.currentWindow.destroy();
    };

    othersUntagged(edgeID) {
        const edge = this.graph.getModel().getCell(edgeID);
        const end1 = edge.getTerminal(true);
        const end2 = edge.getTerminal(false);

        if( end1.getParent().getId().split('_')[0] == 'host' ){
            var netint = end1;
        } else {
            var netint = end2;
        }

        var edges = netint.edges;
        for( let edge of edges) {
            if( edge.getValue() ) {
                var tagged = JSON.parse(edge.getValue()).tagged;
            } else {
                var tagged = true;
            }
            if( !tagged ) {
                return true;
            }
        }
        return false;
    };


    deleteVlanWindow(edgeID) {
        const cell = this.graph.getModel().getCell(edgeID);
        this.graph.removeCells([cell]);
        this.currentWindow.destroy();
    }

    parseVlanWindow(edgeID) {
        //do parsing and data manipulation
        const radios = document.getElementsByName("tagged");
        const edge = this.graph.getModel().getCell(edgeID);

        for(let radio of radios){
            if(radio.checked) {
                //set edge to be tagged or untagged
                if( radio.value == "False") {
                    if( this.othersUntagged(edgeID) ) {
                        document.getElementById("current_window_errors").innerHTML = "Only one untagged vlan per interface is allowed.";
                        return;
                    }
                }
                const edgeVal = {tagged: radio.value == "True"};
                edge.setValue(JSON.stringify(edgeVal));
                break;
            }
        }
        this.graph.refresh(edge);
        this.closeWindow();
    }

    makeMxNetwork(net_name, is_public = false) {
        const model = this.graph.getModel();
        const width = 10;
        const height = 1700;
        const xoff = 400 + (30 * this.netCount);
        const yoff = -10;
        let color = this.netColors[this.netCount];
        if( this.netCount > (this.netColors.length - 1)) {
            color = Math.floor(Math.random() * 16777215); //int in possible color space
            color = '#' + color.toString(16).toUpperCase(); //convert to hex
        }
        const net_val = { name: net_name, public: is_public};
        const net = this.graph.insertVertex(
            this.graph.getDefaultParent(),
            'network_' + this.netCount,
            JSON.stringify(net_val),
            xoff,
            yoff,
            width,
            height,
            'fillColor=' + color,
            false
        );
        const num_ports = 45;
        for(var i=0; i<num_ports; i++){
            let port = this.graph.insertVertex(
                net,
                null,
                '',
                0,
                (1/num_ports) * i,
                10,
                height / num_ports,
                'fillColor=black;opacity=0',
                true
            );
        }

        const ret_val = { color: color, element_id: "network_" + this.netCount };

        this.networks.add(net_name);
        this.netCount++;
        return ret_val;
    }

    addPublicNetwork() {
        const net = this.makeMxNetwork("public", true);
        this.makeSidebarNetwork("public", net['color'], net['element_id']);
        this.has_public_net = true;
    }

    addNetwork(net_name) {
        const ret = this.makeMxNetwork(net_name);
        this.makeSidebarNetwork(net_name, ret.color, ret.element_id);
    }

    updateHosts(removed) {
        const cells = []
        for(const hostID of removed) {
            cells.push(this.graph.getModel().getCell("host_" + hostID));
        }
        this.graph.removeCells(cells);

        const hosts = this.graph.getChildVertices(this.graph.getDefaultParent());
        let topdist = 100;
        for(const i in hosts) {
            const host = hosts[i];
            if(host.id.startsWith("host_")){
                const geometry = host.getGeometry();
                geometry.y = topdist + 50;
                topdist = geometry.y + geometry.height;
                host.setGeometry(geometry);
            }
        }
    }

    makeSidebarNetwork(net_name, color, net_id){
        const colorBlob = document.createElement("div");
        colorBlob.className = "square-20 rounded-circle";
        colorBlob.style['background'] = color;

        const textContainer = document.createElement("span");
        textContainer.className = "ml-2";
        textContainer.appendChild(document.createTextNode(net_name));

        const timesIcon = document.createElement("i");
        timesIcon.classList.add("fas", "fa-times");

        const deletebutton = document.createElement("button");
        deletebutton.className = "btn btn-danger ml-auto square-20 p-0 d-flex justify-content-center";
        deletebutton.appendChild(timesIcon);
        deletebutton.addEventListener("click", function() { this.createDeleteDialog(net_id); }.bind(this), false);

        const newNet = document.createElement("li");
        newNet.classList.add("list-group-item", "d-flex", "bg-light");
        newNet.id = net_id;
        newNet.appendChild(colorBlob);
        newNet.appendChild(textContainer);

        if( net_name != "public" ) {
            newNet.appendChild(deletebutton);
        }
        document.getElementById("network_list").appendChild(newNet);
    }

    makeHost(hostInfo) {
        const value = JSON.stringify(hostInfo['value']);
        const interfaces = hostInfo['interfaces'];
        const width = 100;
        const height = (25 * interfaces.length) + 25;
        const xoff = 75;
        const yoff = this.lastHostBottom + 50;
        this.lastHostBottom = yoff + height;
        const host = this.graph.insertVertex(
            this.graph.getDefaultParent(),
            'host_' + hostInfo['id'],
            value,
            xoff,
            yoff,
            width,
            height,
            'editable=0',
            false
        );
        host.getGeometry().offset = new mxPoint(-50,0);
        host.setConnectable(false);
        this.hostCount++;

        for(var i=0; i<interfaces.length; i++) {
            const port = this.graph.insertVertex(
                host,
                null,
                JSON.stringify(interfaces[i]),
                90,
                (i * 25) + 12,
                20,
                20,
                'fillColor=blue;editable=0',
                false
            );
            port.getGeometry().offset = new mxPoint(-4*interfaces[i].name.length -2,0);
            this.graph.refresh(port);
        }
        this.graph.refresh(host);
    }

    submitForm() {
        const form = document.getElementById("xml_form");
        const input_elem = document.getElementById("hidden_xml_input");
        input_elem.value = this.encodeGraph(this.graph);
        const req = new XMLHttpRequest();
        req.open("POST", "/wf/workflow/", false);
        req.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        req.onerror = function() { alert("problem with form submission"); }
        const formData = $("#xml_form").serialize();
        req.send(formData);
    }
}

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
        takes in a mapping of ids to objects in  items
        and displays them in the dropdown
        */
        const drop = document.getElementById("drop_results");
        while(drop.firstChild)
        {
            drop.removeChild(drop.firstChild);
        }

        for( const id in ids )
        {
            const result_entry = document.createElement("li");
            const result_button = document.createElement("a");
            const obj = this.items[id];
            const result_text = this.generate_element_text(obj);
            result_entry.classList.add("list-group-item", "list-group-item-action");
            result_entry.innerText = result_text;
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
    }

    remove_item(item_id)
    {
        this.added_items.delete(item_id);

        this.update_selected_list()
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

        let list_html = "";

        for( const item_id of this.added_items )
        {
            const item = this.items[item_id];

            const element_entry_text = this.generate_element_text(item);

            list_html += '<div class="border rounded mt-2 w-100 d-flex align-items-center pl-2">'
                + element_entry_text
                + '<button onclick="searchable_select_multiple_widget.remove_item('
                + item_id
                + ')" class="btn btn-danger ml-auto">Remove</button>';
            list_html += '</div>';
        }
        added_list.innerHTML = list_html;
    }
}
