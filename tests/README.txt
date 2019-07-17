This folder contains the tools needed to unit test the frontend
JavaScript files using Karma, Mocha, and Chai.


Getting started:
Install NPM if you haven't:
https://nodejs.org/en/download/package-manager/

Run 'npm install' to install all required dependencies in this
folder.

Run 'npm test' to run current unit tests.


Adding tests:
Tests are located in the tests/ folder, you can simply edit the
existing ones or create a new one by making a file with the .js
file extension.

Karma is used for launching different browsers to run JavaScript.
See Karma documentation at https://karma-runner.github.io/
to add more browsers, files to test, or frameworks.

Mocha is used for the structure of the JavaScript testing itself.
See Mocha documentation at https://mochajs.org/ to see the syntax
required to create/modify tests. Currently, the tests use the
'TDD' interface from Mocha.

Chai is used for the actual testing, with it being an assertion
library. See Chai documentation at https://www.chaijs.com/ to see
the available usages for assertion. The tests use the 'assert' API
along with Mocha's TDD interface.
