-----------------------------------------------------------------------------
   Copyright (c) 2025 Magda Kowalska. All rights reserved.
 
   This software and its source code are the intellectual property of
   Magda Kowalska. Unauthorized copying, reproduction, or use of this
   software, in whole or in part, is strictly prohibited without express
   written permission.
 
   This software is protected under the Berne Convention for the Protection
   of Literary and Artistic Works, EU copyright law, and international
   copyright treaties.
 
   Author: Magda Kowalska
   
   Created: 2025-11-02
   
   Last Modified: 2025-11-02
   
------------------------------------------------------------------------------

This is my code for the Jump coding project for an AI Smart Email Sorter.

Deployed using Render at https://smartsort-0yhb.onrender.com/

Features:
- Gmail login via OAuth
- Adding new categories
- Anthropic Claude API is used for processing and assinging new emails to categories
- Emails that don't fit any existing category are put in Uncategorized
- Smart unsubscribe functionality that uses BeautifulSoup (check console for the results of unsubscribe processing)
- New emails from Gmail (only unread and in inbox) are processed in batches of 10 at once
- Due to Render.com free tier limitations the background task run may not be guaranteed, please refresh the page if new Categories are not being refreshed automatically after 5 minutes. It should always work when you press the Process New Emails Button

Preview:

<img width="1277" height="811" alt="Screenshot 2025-11-02 at 16 49 10" src="https://github.com/user-attachments/assets/1fb695ca-3db2-421f-bb6f-cdf9a181078f" />










