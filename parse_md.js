const fs = require('fs');

// Read the contents of the Markdown file
fs.readFile('response.md', 'utf8', (err, data) => {
  if (err) {
    console.error('Error reading file:', err);
    return;
  }

  // Parse the JSON data from the Markdown file
  const markdownData = JSON.parse(data);

  // Extract question and options
  const { output_text } = markdownData;
  const { question, options } = extractQuestionAndOptions(output_text);

  // Convert options to an array
  const optionsArray = options.split(' ').filter(option => option !== '');

  // Construct HTML for the multiple-choice question with tick boxes
  const mcqHTML = `
    <div>
      <p>${question}</p>
      <ul>
        ${optionsArray.map((option, index) => `
          <li>
            <input type="checkbox" id="option${index + 1}" name="options" value="${option}">
            <label for="option${index + 1}">${option}</label>
          </li>
        `).join('')}
      </ul>
    </div>
  `;

  // Write the HTML to an HTML file
  fs.writeFile('output.html', mcqHTML, (err) => {
    if (err) {
      console.error('Error writing HTML file:', err);
      return;
    }
    console.log('HTML file generated successfully!');
  });
});

// Function to extract question and options from the output_text
function extractQuestionAndOptions(output_text) {
  const regex = /question:(.*)option1:(.*)option2:(.*)option3:(.*)option4:(.*)/;
  const match = output_text.match(regex);
  if (match) {
    const [, question, option1, option2, option3, option4] = match;
    return {
      question: question.trim(),
      options: `${option1.trim()} ${option2.trim()} ${option3.trim()} ${option4.trim()}`
    };
  } else {
    return {
      question: '',
      options: ''
    };
  }
}
