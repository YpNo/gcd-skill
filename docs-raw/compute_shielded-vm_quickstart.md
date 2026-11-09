# Quickstart: Enable Shielded VM options

Source: https://berlin.devsitetest.how/compute/shielded-vm/docs/quickstart
Last updated: 2026-11-06

Some or all of the information on this page might not apply to Google Cloud Dedicated. See [Differences from Google Cloud](/compute/shielded-vm/docs/tpc-differences) for more details.














- 





[

Home

](https://berlin.devsitetest.how/)






- 








[

Documentation

](https://berlin.devsitetest.how/docs)






- 








[

Compute

](https://berlin.devsitetest.how/docs/compute-area)






- 








[

Compute Engine

](https://berlin.devsitetest.how/compute/docs)






- 








[

Shielded VM

](https://berlin.devsitetest.how/compute/shielded-vm/docs)






- 








[

Guides

](https://berlin.devsitetest.how/compute/shielded-vm/docs/shielded-vm)


























# Quickstart: Enable Shielded VM options




Learn how to enable Shielded VM options by using the Google Cloud Dedicated console.





## Before you begin



Before you start this tutorial, complete the following steps:

- Create a VM instance with
[an OS that supports Shielded VM features](/compute/docs/images/os-details#security-features).
Learn more about
[creating a VM instance](/compute/docs/instances/create-start-instance).

- 

Verify that you have the following permissions on the VM.

- `compute.instances.updateShieldedInstanceConfig`

Learn more about
[managing access to Compute Engine resources](/compute/docs/access/managing-access-to-resources).






## Enable all Shielded VM options

- 

In the Google Cloud Dedicated console, go to the **VM instances** page.

[Go to **VM instances**](https://console.cloud.berlin-build0.goog/compute/instances) 

- 

Click the instance name to open the **VM instance details** page.

- 

Click stop **Stop**. If there is no **Stop** option, click
more_vert **More actions >** stop **Stop**.

- 

After the instance stops, click **Edit**.

- 

In the **Shielded VM** section, modify the Shielded VM options:

- Toggle **Turn on Secure Boot** to enable Secure Boot. Learn more about
[Secure Boot](/compute/shielded-vm/docs/shielded-vm#secure-boot).

- Toggle **Turn on vTPM** to enable the virtual trusted platform module
(vTPM). Learn more about [vTPM](/compute/shielded-vm/docs/shielded-vm#vtpm).

- Toggle **Turn on Integrity Monitoring** to enable integrity
monitoring. Learn more about
[integrity monitoring](/compute/shielded-vm/docs/shielded-vm#integrity-monitoring).

- 

Click **Save**.

- 

Click **Start** to start the instance.






## Clean up





To avoid incurring charges to your Google Cloud Dedicated account for
the resources used on this page, follow these steps.






- 

In the Google Cloud Dedicated console, go to the **VM instances** page.

[Go to **VM instances**](https://console.cloud.berlin-build0.goog/compute/instances) 

- 

In the row for the VM instance you created for this exercise, click **More
Actions**, and then select **Delete**.






## What's next



- Learn more about the [key concepts in Shielded VM](/compute/shielded-vm/docs/shielded-vm).

- Learn more about [modifying Shielded VM options](/compute/shielded-vm/docs/modifying-shielded-vm).