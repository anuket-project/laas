/* Used to manage the add_collaborators widget 
    - async .init([string,]) (userIpas) -> void : Must be after construction to load initial values from the API, and allows loading of pre-selected, permanent, users  
    - .isValid() -> bool : Tests if the collaborator field is valid
        Mainly tests if search bar is empty
    - .getCollaboratorIds() -> [int,] (userIds) : Gets array of selected collaborators ids 
    - .getCollaboratorNames() -> [string,] (userIpas) : : Gets array of selected collaborators names
    - .makeSelectionPermanent() -> void : Removes all X buttons so the user is locked into their current selection and retains current selection between clearCurrentSelection() uses 
    - .clearCurrentSelection() -> void : Removes all non-permanent selections the user has made
*/
class addCollaboratorWidget {
    
    #publicUsers = null; 
    /*
    {
        id :{
            'ipa': ,
            'full_name': ,
            'email': ,
        },
    }
    */
    #selectedUsers = new Map();
    #selectedUsersPermanent = new Map();
    // {userId: userIpa}

    #selectedUserElementTemplate = document.createElement("li"); 
    #userDropdownOptionTemplate = document.createElement("a");


    constructor (
    ) {
        this.#selectedUserElementTemplate.classList.add("list-group-item", "d-flex", "align-items-center", "py-1", "px-2");
        let textField = document.createElement("div");
        textField.classList.add("col", "overflow-ellipsis", "addCollab_selectedUserText", "py-1");
        
        let buttonHold = document.createElement("div");
        buttonHold.classList.add("col-auto");

        let button = document.createElement("button");
        button.classList.add("btn", "fas", "fa-times");

        buttonHold.appendChild(button);
        this.#selectedUserElementTemplate.appendChild(textField);
        this.#selectedUserElementTemplate.appendChild(buttonHold);

       
        // Set semantics of <a> to be a button rather than a link
        this.#userDropdownOptionTemplate.classList.add("list-group-item", "list-group-item-action", "overflow-ellipsis", "flex-shrink-0");
        this.#userDropdownOptionTemplate.setAttribute("role", "button")
        this.#userDropdownOptionTemplate.setAttribute("tabindex", "0")
        
    }

    // Separate from constructor due to async 
    async init(
        users, // [string] (ipa usernames)
    ) {
        this.#addStaticEventListeners();

        this.#publicUsers = await this.#getPubUsers();
        
        for (let user of users) {
            await this.#queryForUser(user, false)
        }

        this.#selectedUsersPermanent = new Map(this.#selectedUsers)
        
    }


    getCollaboratorIds() {
        let retIds = []

        this.#selectedUsers.forEach((val, key) => {
            retIds.push(key)
        })


        return retIds;
    }

    getCollaboratorNames() {
        let retIds = []

        this.#selectedUsers.forEach((val, key) => {
            retIds.push(val)
        })


        return retIds;
    }



    isValid() {
        return (document.getElementById("addCollab_search").value === "")
    }


    makeSelectionPermanent() {
        const selectedList = document.getElementById("addCollab_selectedUsers");

        for (let collab_user of selectedList.children) {
            // Skip the p element with the no collaborator notice text 
            if (collab_user.tagName !== "P") {
                collab_user.lastElementChild.setAttribute("hidden", "")
            }
            
        }

        this.#selectedUsersPermanent = new Map(this.#selectedUsers)
        
    }


    clearCurrentSelection() {
        for (let userInfo of this.#selectedUsers) {
            if (!this.#selectedUsersPermanent.has(Number(userInfo[0]))) {
                document.getElementById("addCollab_selectedUser_" + userInfo[0]).remove()
            }
        }

        this.#selectedUsers = new Map(this.#selectedUsersPermanent)    
        
    }

    clearSearchBar() {
        document.getElementById("addCollab_search").value = "";
    }

    
    #addStaticEventListeners() {

        document.getElementById("addCollab_search").addEventListener("keyup", async ({key}) =>  {
            let elem = document.getElementById("addCollab_search")
            elem.classList.remove("is-invalid")

            let elemVal = elem.value
            if (key === "Enter") {
                await this.#queryForUser(elemVal, true);
            } else {
                this.#updateDropdownUserOptions(elemVal);
            };
        });

        document.getElementById("addCollab_button").addEventListener("click", async () => {
            let elemVal = document.getElementById("addCollab_search").value
            await this.#queryForUser(elemVal, true);
        });



    }

    async #getPubUsers() {
        const token = document.getElementsByName('csrfmiddlewaretoken')[0].value

        return JSON.parse(await new Promise((resolve, reject) => {// -> HttpResponse
            $.ajax(
              {
              url: '/accounts/users/collaborators',
              type: 'get',
              headers: {
                'X-CSRFToken': token,
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
          }));
    }



    #updateDropdownUserOptions(search) {
       
        const dropdown = document.getElementById("addCollab_dropdownOptions");
        while(dropdown.firstChild) {
            dropdown.removeChild(dropdown.lastChild);
        }

        if (search.length === 0) {
            return;
        }

        search = search.toLocaleUpperCase("en-US");

        for(const userId in this.#publicUsers) {
            let userObj = this.#publicUsers[userId];

            if (!this.#selectedUsers.has(Number(userId)) && ((userObj.ipa.toLocaleUpperCase("en-US").startsWith(search) || userObj.full_name.toLocaleUpperCase("en-US").startsWith(search) || userObj.email.toLocaleUpperCase("en-US").startsWith(search)))) {
            
                let newUserDropdownOption = this.#userDropdownOptionTemplate.cloneNode(true);
                
                dropdown.append(newUserDropdownOption);

                // Can't edit the node because the specific properties do not exist in nodes, only elements
                dropdown.lastElementChild.id = "addCollab_dropdownOptions_" + userId;
                dropdown.lastElementChild.textContent = userObj.ipa + ", " + userObj.email;
                dropdown.lastElementChild.addEventListener("click", () => {

                    this.#addSelectedUser(userId, userObj, true);

                })

            }

        }
    }


    
    async #queryForUser(search, canDelete) {

        if (search.length === 0) {
            return;
        }

        
        search = search.toLocaleUpperCase("en-US").trim();


        // Check public users locally
        for(const id in this.#publicUsers) {
            let userObj = this.#publicUsers[id];

            if (userObj.ipa.toLocaleUpperCase("en-US").localeCompare(search) === 0 || userObj.full_name.toLocaleUpperCase("en-US").localeCompare(search) === 0 || userObj.email.toLocaleUpperCase("en-US").localeCompare(search) === 0) {
                this.#addSelectedUser(id, userObj, canDelete)
                return;
            }

        }


        const token = document.getElementsByName('csrfmiddlewaretoken')[0].value
        // Check private via API
        let apiResponse = JSON.parse(await new Promise((resolve, reject) => {// -> HttpResponse
            $.ajax(
              {
              url: '/accounts/users/collaborators/validate',
              type: 'get',
              data: {"query": search},
              headers: {
                'X-CSRFToken': token,
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
        }));

        if (apiResponse.is_user === false) {
            document.getElementById("addCollab_search").classList.add("is-invalid");
            return;           
        }

        let userObj = {
            'ipa': apiResponse.ipa,
            'full_name': '',
            'email': apiResponse.email,
        }

        this.#addSelectedUser(apiResponse.id, userObj, canDelete);

    }


    #addSelectedUser(
        userId, 
        userObj, 
        canDelete, // Whether or not to display the X button to allow user to remove user 
    ) {
        if (this.#selectedUsers.has(Number(userId))) {
            return;
        }

        this.#selectedUsers.set(Number(userId), userObj.ipa)


        document.getElementById("addCollab_noCollaboratorNotice").setAttribute("hidden", "")

        document.getElementById("addCollab_search").value = "";
        this.#updateDropdownUserOptions(document.getElementById("addCollab_search").value);


        let newSelectedUser = this.#selectedUserElementTemplate.cloneNode(true);
        let selectedUserList = document.getElementById("addCollab_selectedUsers");

        selectedUserList.appendChild(newSelectedUser);

        // Can't do node edit because the specific properties do not exist in nodes, only elements
        selectedUserList.lastElementChild.id = "addCollab_selectedUser_" + userId;
        selectedUserList.lastElementChild.firstElementChild.textContent = userObj.ipa + ", " + userObj.email;

        if (canDelete) {
            selectedUserList.lastElementChild.lastElementChild.addEventListener("click", () => {
                this.#selectedUsers.delete(Number(userId));

                document.getElementById("addCollab_selectedUser_" + userId).remove()

                if (this.#selectedUsers.size === 0) {
                    document.getElementById("addCollab_noCollaboratorNotice").removeAttribute("hidden")
                }

            });
        } else {
            selectedUserList.lastElementChild.lastElementChild.setAttribute("hidden", "")
        }


    }




}