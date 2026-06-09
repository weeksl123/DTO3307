# Testing

## Sign up/in pages

|    Input    |  Expected Result  |  Actual Result  |  Changes Made  |
|:-----------:|:-----------------:|:---------------:|:--------------:|
| Number in the Username box | Accepts it | Exactly as expected | None |
| Invalid email: "example@e" | Flags it and account creation doesn't happen | Accepts it | Added backend verification and a domain check |
| Passwords that don't match: "Leaf1234/Leaf1233" | Says "Passwords don't match" and doesn't accept it | Exactly as expected | None |

## Dashboard

|    Input    |  Expected Result  |  Actual Result  |  Changes Made  |
|:-----------:|:-----------------:|:---------------:|:--------------:|
| Take $50 from child 1 | $50 taken from child 1 balance and in turn chart | Exactly as expected | None |
| Reverse the $50 from child 1 | $50 added to child 1 balance and chart | Exactly as expected | None |
| Clicking the add child button | Takes you to the child account creation page | Exactly as expected | None |
| Clicking the remove child button | Asks if you're sure and if so deletes the child account| Exactly as expected | None |

## Settings

|    Input    |  Expected Result  |  Actual Result  |  Changes Made  |
|:-----------:|:-----------------:|:---------------:|:--------------:|
| Clicking the "Darkmode" toggle | Toggles darkmode | Exactly as expected | None |
| Changing the Annual allowance | Changes the allowance without any errors | Exactly as expected | None |
| Change parent account password| Parent account password changes | Exactly as expected | None |
| Change child account password| Child account password changes | Exactly as expected | None |

## Testing Video

- Watch the [Testing Video Here](./DTO3307%20Testing%20Video.mp4) (Please do not mind the screen going black when changing pages, I am unsure as to why this was happening but it is a problem with OBS not the website)
