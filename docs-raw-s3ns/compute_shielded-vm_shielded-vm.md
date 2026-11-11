# Shielded VM overview

Source: https://documentation.s3ns.fr/compute/shielded-vm/docs/shielded-vm
Last updated: 2026-11-10

Some or all of the information on this page might not apply to Cloud de Confiance by S3NS. See [Differences from Google Cloud](/compute/shielded-vm/docs/tpc-differences) for more details.














- 





[

Home

](https://documentation.s3ns.fr/)






- 








[

Documentation

](https://documentation.s3ns.fr/docs)






- 








[

Compute

](https://documentation.s3ns.fr/docs/compute-area)






- 








[

Compute Engine

](https://documentation.s3ns.fr/compute/docs)






- 








[

Shielded VM

](https://documentation.s3ns.fr/compute/shielded-vm/docs)






- 








[

Guides

](https://documentation.s3ns.fr/compute/shielded-vm/docs/shielded-vm)












# Shielded VM overview 















This page discusses key concepts and terminology for Shielded VM. To
get started using Shielded VM, try the [quickstart](/compute/shielded-vm/docs/quickstart) or
see [Modifying Shielded VM options](/compute/shielded-vm/docs/modifying-shielded-vm).

Shielded VM offers verifiable integrity of your Compute Engine VM
instances, so you can be confident your instances haven't been compromised by
boot- or kernel-level
[malware](https://en.wikipedia.org/wiki/Malware) or
[rootkits](https://en.wikipedia.org/wiki/Rootkit).

## Key benefits of Shielded VMs

Shielded VMs deliver multiple strategic advantages such as
comprehensive protection against firmware-level attacks, bootloader
modifications, and kernel-level compromises.

- 

**Operational benefits:** include reduced security incident response time,
simplified compliance management, and enhanced visibility into system
integrity.

- 

**Business advantages:** include increased confidence in cloud infrastructure,
reduced risk of security breaches, and improved regulatory compliance posture.

## Core security architecture of Shielded VMs

Shielded VMs implement a triple shield architecture. This architecture
provides robust protection from the ground up as described in the following
table.




| 
Feature | 
What it is | 
How it helps | 
|



| 
Secure boot technology | 
A UEFI firmware feature that ensures your VM boots only with
authentic, signed software by verifying the digital signature of all
boot components such as firmware drivers, OS bootloader, and the kernel.


For more information, see [Secure boot](#secure-boot). | 
Prevents unauthorized or tampered bootloaders and kernels from
loading, stopping many bootkits and rootkits. Halts the boot process if a
component lacks a trusted signature.
| 
|

| 
Virtual trusted platform module (vTPM) | 
A virtualized security processor, providing each Shielded VM
with a dedicated vTPM for hardware-level security.


For more information, see [Virtual trusted platform module (vTPM)](#vtpm). | 

Provides the following features:



- **Measured boot:** Takes cryptographic hashes of critical boot
components such as firmware, bootloader, kernel, and drivers and
stores them securely, creating a verifiable boot chain.

- **Secure key generation and storage:** Generates and stores
cryptographic keys, for example, for BitLocker, releasing them only if
the measured boot verifies the boot state as trusted.


| 
|

| 
Advanced integrity monitoring | 
A monitoring system that establishes a golden baseline of boot
measurements taken during the measured boot.


For more information, see [Integrity monitoring](#integrity-monitoring). | 
Compares current boot measurements against the trusted baseline on
subsequent boots. Generates alerts in Cloud Logging and Security Command Center if
it detects discrepancies, enabling proactive investigation of potential
integrity violations. | 
|



### Secure Boot

Secure Boot helps ensure that the system only runs authentic software by
verifying the digital signature of all boot components, and halting the boot
process if signature verification fails.

Shielded VM instances run Google-built UEFI firmware. As an additional
layer of security, and in line with standard Google practices for all its
production software, this firmware is cryptographically signed and verified
using Google's internal Certificate Authority, and this validation is done on
all firmware, regardless of whether the Secure Boot feature is enabled. This
verification ensures the firmware's integrity, confirming it's authentic and
unmodified and establishing the [root of trust](https://uefi.org/sites/default/files/resources/UEFI%20RoT%20white%20paper_Final%208%208%2016%20%28003%29.pdf) 
for Secure Boot.

The [Unified Extensible Firmware Interface (UEFI) 2.3.1
firmware](https://uefi.org/sites/default/files/resources/UEFI_Secure_Boot_in_Modern_Computer_Security_Solutions_2013.pdf),
securely manages the certificates that contain the keys used by the software
manufacturers to sign the system firmware, the system boot loader, and any
binaries they load. Shielded VM instances use UEFI firmware.

On each boot, the UEFI firmware verifies the digital signature of each boot
component against the secure store of approved keys. Any boot component that
isn't properly signed, or isn't signed at all, isn't allowed to run.

If this occurs, the VM instance's
[serial console](/compute/docs/instances/interacting-with-serial-console) log
will have an entry containing the strings **UEFI: Failed to load image** and
**Status: Security Violation**, along with a description of the boot
option that failed. To troubleshoot the failure, disable Secure Boot by
using the instructions in [Modifying Shielded VM
options](/compute/shielded-vm/docs/modifying-shielded-vm) so that you can boot the
VM instance, diagnose and resolve the issue, then re-enable Secure Boot.

### Virtual Trusted Platform Module (vTPM)

A vTPM is a virtualized [trusted platform
module](https://trustedcomputinggroup.org/trusted-platform-module-tpm-summary/),
which is a specialized computer chip you can use to protect objects, like keys
and certificates, that you use to authenticate access to your system. The
Shielded VM vTPM is fully compatible with the
[Trusted Computing Group (TPM) library specification 2.0](https://trustedcomputinggroup.org/tpm-library-specification/)
and uses the [BoringSSL library](https://boringssl.googlesource.com/boringssl/).
The BoringSSL library relies on the BoringCrypto module. For FIPS 140-3 details
about the BoringCrypto module, see [NIST Cryptographic Module Validation Program Certificate #5244](https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/5244).

The Shielded VM vTPM enables [Measured Boot](#measured-boot) by
performing the measurements needed to create a known good boot baseline, called
the *integrity policy baseline*. The integrity policy baseline is used for
comparison with measurements from subsequent VM boots to determine if anything
has changed.

You can also use the vTPM to protect secrets through shielding or
[sealing](https://en.wikipedia.org/wiki/Trusted_Computing#SEALED-STORAGE).
See the [Go-TPM](https://github.com/google/go-tpm) project on
GitHub for Go language examples that illustrate how to use a vTPM for this
purpose.

### Measured Boot

During Measured Boot, a hash of each component (for example, the firmware,
bootloader, or kernel) is created as the component is loaded, and that hash is
then concatenated and rehashed with the hashes of any components that have
already been loaded, as illustrated here:



This information identifies both the components that were loaded, and their
load order.

The first time you boot a VM instance, Measured Boot creates the integrity
policy baseline from the first set of these measurements, and securely stores
this data. Each time the VM instance boots after that, these measurements are
taken again, and stored in secure memory until the next reboot. Having these two
sets of measurements enables [integrity monitoring](#integrity-monitoring),
which you can use to determine if there have been changes to a VM instance's
boot sequence.

### Integrity monitoring

Integrity monitoring helps you understand and make decisions about the state of
your VM instances.

Integrity monitoring relies on the measurements created by Measured Boot,
which use
[platform configuration registers](https://link.springer.com/chapter/10.1007/978-1-4302-6584-9_12)
(PCRs) to store information about the components and component load order of
both the integrity policy baseline (a known good boot sequence),
and the most recent boot sequence.

Integrity monitoring compares the most recent boot measurements to the integrity
policy baseline and returns a pair of pass or fail results depending on whether
they match or not, one for the early boot sequence and one for the late boot
sequence. Early boot is the boot sequence from the start of the UEFI firmware
until it passes control to the bootloader. Late boot is the boot sequence from
the bootloader until it passes control to the operating system kernel. If either
part of the most recent boot sequence doesn't match the baseline, you get an
integrity validation failure.

If the failure is expected, for example if you applied a system update on that
VM instance, you should [update the integrity policy baseline](/compute/shielded-vm/docs/integrity-monitoring#updating-baseline).
Updating the integrity policy baseline sets the baseline to the measurements
captured from the most recent boot sequence. If it is not expected, you should stop
that VM instance and investigate the reason for the failure.

You can view integrity reports in Cloud Monitoring, and set alerts on
integrity failures. You can review the details of integrity monitoring results
in Cloud Logging. For more information, see [Monitoring integrity on Shielded VM instances](/compute/shielded-vm/docs/integrity-monitoring).

#### Integrity monitoring events

Shielded VM creates log entries for the following types of events:

- `clearTPMEvent`: Identifies if the vTPM has been cleared, which deletes any
secrets stored in it. This doesn't affect any aspect of Shielded VM,
so you will only care about this if you use the vTPM to shield sensitive data
as described in [Virtual Trusted Platform Module
(vTPM)](#vtpm).

- `earlyBootReportEvent`: Identifies whether the early boot sequence integrity
check passed, and provides details on the PCR values from the baseline and
the most recent boot sequence that were compared to make that determination.

- `lateBootReportEvent`: Identifies whether the late boot sequence integrity
check passed, and provides details on the PCR values from the baseline and
the most recent boot sequence that were compared to make that determination.

- `setShieldedInstanceIntegrityPolicy`: Logged each time you update the integrity
policy baseline.

- `shutdownEvent`: Logged each time the VM instance is stopped.

- `startupEvent`: Logged each time the VM instance is started. The interesting
information in this event is the `bootCounter` value, which identifies how
many times this instance has been restarted.

- `updateShieldedInstanceConfig`: Logged each time you enable or disable one of
the Shielded VM options.

The typical event progression you see in the logs is `startupEvent`,
`earlyBootReportEvent`, `lateBootReportEvent`, and eventually `shutdownEvent`,
all with the same `bootCounter` value to identify them as describing the same
VM instance boot sequence.

If you update the integrity policy baseline in response to an
expected integrity failure on a VM instance, you will see additional
`earlyBootReportEvent` and `lateBootReportEvent` events that describe the new
integrity policy baseline measurements. The following example shows the
expected sequence:

- `startupEvent`

- `earlyBootReportEvent` that compares original baseline to latest boot
sequence (passes)

- `lateBootReportEvent` that compares original baseline to latest boot
sequence (fails)

- `setShieldedInstanceIntegrityPolicy` when you [update the integrity policy
baseline](/compute/shielded-vm/docs/integrity-monitoring#updating-baseline),
which sets the baseline to the measurements captured from the latest boot
sequence

- `earlyBootReportEvent` that compares new baseline to latest boot sequence
(passes)

- 

`lateBootReportEvent` that compares new baseline to latest boot sequence
(passes)



### Windows

#### earlyBootReportEvent

`earlyBootReportEvent` contains the following sections and elements:

- 

`actualMeasurements`: Contains the [platform configuration
register](https://link.springer.com/chapter/10.1007/978-1-4302-6584-9_12)
(PCR) values for the latest boot sequence. The PCR values are what
identify the boot components and component load order used by the latest
boot sequence, and are what are compared to the integrity policy baseline
(whose values are captured in the `policyMeasurements` section) to
determine if there has been any change in the VM instance boot sequence.
The elements of the `actualMeasurements` section can vary, based on the
OS, distribution, and configuration. The section typically includes the
following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
UEFI boot manager code and boot attempts.

- `2`: Contains the value for PCR5, which contains information about the
disk's GUID partition table. It is not used when validating the latest
boot sequence against the integrity policy baseline.

- `3`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

- 

`policyEvaluationPassed`: Identifies whether the given section of the boot
sequence passed verification against the integrity policy baseline.

- 

`policyMeasurements`: Contains the baseline PCR values that integrity
validation uses as expected values. The `policyMeasurements` section can
vary based on the OS, distribution and configuration, but typically
includes the following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
UEFI boot manager code and boot attempts. This value is not included
in first boot.

- `2`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

To learn how to use `earlyBootReportEvent` PCR values to diagnose a boot
integrity validation failure, see [Determining the cause of boot integrity
validation
failure](/compute/shielded-vm/docs/integrity-monitoring#diagnosing-failure).

#### lateBootReportEvent

`lateBootReportEvent` contains the following sections and elements:

- 

`actualMeasurements`: Contains the [platform configuration register](https://link.springer.com/chapter/10.1007/978-1-4302-6584-9_12)
(PCR) values for the latest boot sequence. The PCR values are what
identify the boot components and component load order used by the latest
boot sequence, and are what are compared to the integrity policy baseline
(whose values are captured in the `policyMeasurements` section) to
determine if there has been any change in the VM instance boot sequence.
The elements of the `actualMeasurements` section can vary, based on the
OS, distribution, and configuration. The section typically includes the
following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
UEFI boot manager code and boot attempts.

- `2`: Contains the value for PCR5, which contains information about the
disk's GUID partition table. It is not used when validating the latest
boot sequence against the integrity policy baseline.

- `3`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

- `4`: Contains the value for PCR11, which contains information about
BitLocker Drive Encryption access control.

- `5`: Contains the value for PCR12, which contains information about data
events. It is not used when validating the latest
boot sequence against the integrity policy baseline.

- `6`: Contains the value for PCR13, which contains information about
Windows kernel and boot drivers.

- `7`: Contains the value for PCR14, which contains information about
Windows boot authorities.

- 

`policyEvaluationPassed`: Identifies whether the given section of the boot
sequence passed verification against the integrity policy baseline.

- 

`policyMeasurements`: Contains the baseline PCR values that integrity
validation uses as expected values. The `policyMeasurements` section can
vary based on the OS, distribution and configuration, but typically
includes the following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
UEFI boot manager code and boot attempts.

- `2`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

- `3`: Contains the value for PCR11, which contains information about
BitLocker Drive Encryption access control.

- `4`: Contains the value for PCR13, which contains information about
Windows kernel and boot drivers.

- `5`: Contains the value for PCR14, which contains information about
Windows boot authorities.

To learn how to use `lateBootReportEvent` PCR values to diagnose a boot
integrity validation failure, see [Determining the cause of boot integrity
validation
failure](/compute/shielded-vm/docs/integrity-monitoring#diagnosing-failure).


### Linux

#### earlyBootReportEvent

`earlyBootReportEvent` contains the following sections and elements:

- 

`actualMeasurements`: Contains the [platform configuration
register](https://link.springer.com/chapter/10.1007/978-1-4302-6584-9_12)
(PCR) values for the latest boot sequence. The PCR values are what
identify the boot components and component load order used by the latest
boot sequence, and are what are compared to the integrity policy baseline
(whose values are captured in the `policyMeasurements` section) to
determine if there has been any change in the VM instance boot sequence.
The elements of the `actualMeasurements` section can vary, based on the
OS, distribution, and configuration. The section typically includes the
following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
operating system shim.

- `2`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

- 

`policyEvaluationPassed`: Identifies whether
the given section of the boot sequence passed verification against the
integrity policy baseline.

- 

`policyMeasurements`: Contains the baseline PCR values that integrity
validation uses as expected values. The `policyMeasurements` section can
vary based on the OS, distribution and configuration, but typically
includes the following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
operating system shim. This value is not included in first boot.

- `2`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

To learn how to use `earlyBootReportEvent` PCR values to diagnose a boot
integrity validation failure, see [Determining the cause of boot integrity
validation
failure](/compute/shielded-vm/docs/integrity-monitoring#diagnosing-failure).

#### lateBootReportEvent

`lateBootReportEvent` contains the following sections and elements:

- 

`actualMeasurements`: Contains the [platform configuration
register](https://link.springer.com/chapter/10.1007/978-1-4302-6584-9_12)
(PCR) values for the latest boot sequence. The PCR values are what
identify the boot components and component load order used by the latest boot
sequence, and are what are compared to the integrity policy baseline
(whose values are captured in the `policyMeasurements` section) to
determine if there has been any change in the VM instance boot sequence.
The elements of the `actualMeasurements` section can vary, based on the
OS, distribution, and configuration. The section typically includes the
following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
second stage boot loader and the kernel.

- `2`: Contains the value for PCR5, which contains information about the
disk's GUID partition table. It is not used when validating the latest
boot sequence against the integrity policy baseline.

- `3`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

- 

`policyEvaluationPassed`: Identifies whether
the given section of the boot sequence passed verification against the
integrity policy baseline.

- 

`policyMeasurements`: Contains the baseline PCR values that integrity
validation uses as expected values. The `policyMeasurements` section can
vary based on the OS, distribution and configuration, but typically
includes the following elements:

- `0`: Contains the value for PCR0, which contains information about
firmware components and the memory encryption technology that is
active. This PCR diverges from the [TCG PCClient platform firmware
profile](https://trustedcomputinggroup.org/resource/%0Apc-client-specific-platform-firmware-profile-specification/) in that
it measures only the following events:

- `EV_S_CRTM_VERSION`, the Compute Engine firmware version

- `EV_NONHOST_INFO`, representing the
[memory encryption technology](/confidential-computing/confidential-vm/docs/confidential-vm-overview)

- `EV_SEPARATOR`, the specified delimiter event firmware measures
when it will add no more PCR0 events.
This means PCR0 has a static value for the lifetime of a VM. The value
only changes for new VMs after major version firmware updates or
change in encryption technology. It is not used when validating the
latest boot sequence against the integrity policy baseline.

- `1`: Contains the value for PCR4, which contains information about the
second stage boot loader and the kernel.

- `2`: Contains the value for PCR7, which contains information about the
instance's Secure Boot policy.

To learn how to use `lateBootReportEvent` PCR values to diagnose a boot
integrity validation failure, see [Determining the cause of boot integrity
validation
failure](/compute/shielded-vm/docs/integrity-monitoring#diagnosing-failure).



## Using BitLocker with Shielded VM images

You can enable BitLocker for Windows boot disks that are part of
Shielded VM images. Shielded VM images offer security features
such as UEFI-compliant firmware, Secure Boot, vTPM-protected Measured Boot, and
integrity monitoring. vTPM and integrity monitoring are enabled by default, and
Google recommends [enabling Secure Boot if
possible](/compute/shielded-vm/docs/modifying-shielded-vm).

If you choose to enable BitLocker on a Windows boot disk that is part of a
Shielded VM image, we strongly recommend saving the recovery key to a
safe location, because if you don't have the recovery key, you can't recover the
data.

Take the following into account before enabling BitLocker on a Windows boot disk
that is part of a Shielded VM image:

- 

On Shielded VM boot disks, BitLocker uses the vTPM to store the
encryption keys, and the vTPM is permanently associated with the VM on which it
was created. This means that you can restore a snapshot of a
Shielded VM boot disk to another persistent disk, but you can't decrypt
it because the vTPM containing the BitLocker keys isn't available. If you have
a recovery key, you can recover data by following the instructions in the
[BitLocker recovery guide](https://docs.microsoft.com/en-us/windows/security/information-protection/bitlocker/bitlocker-recovery-guide-plan).
If you don't have a recovery key, the data on the disk is unrecoverable.

- 

On Shielded VM data disks, persistent disk data is encrypted by
default. Enabling BitLocker on top of persistent disk encryption doesn't affect
throughput, but it might increase vCPU utilization slightly. Enabling BitLocker
on data disks that are attached to the VM doesn't pose the same recovery
challenges as for boot disks. This is because the BitLocker encryption keys for
data disks aren't stored on the vTPM. If you have lost the ability to unlock the
disk normally and have the recovery key, you can attach the disk to another
unencrypted VM and recover it from there. If you don't have a recovery key, the
data on the disk is unrecoverable.

## Identity and Access Management authorization

Shielded VM uses IAM for authorization.

Shielded VM operations use the following Compute Engine
permissions:

- `compute.instances.updateShieldedInstanceConfig`: Allows the user to change
the Shielded VM options on a VM instance.

- `compute.instances.setShieldedInstanceIntegrityPolicy`: Allows the user to
update the integrity policy baseline on a VM instance.

- `compute.instances.getShieldedInstanceIdentity`: Allows the user to retrieve
endorsement key information from the vTPM.

Shielded VM permissions are granted to the following Compute Engine
roles:

- `roles/compute.instanceAdmin.v1`

- `roles/compute.securityAdmin`

You can also grant Shielded VM permissions to [custom
roles](/iam/docs/creating-custom-roles).

## Organization policy constraints for Shielded VM

You can set the `constraints/compute.requireShieldedVm` [organization policy
constraint](/resource-manager/docs/organization-policy/org-policy-constraints)
to `True` to require that Compute Engine VM instances created in your
organization be Shielded VM instances.

Learn how to set the `constraints/compute.requireShieldedVm` constraint in
[Using boolean constraints in organization
policy](/resource-manager/docs/organization-policy/using-constraints#boolean-constraint).
You must be an [organization policy
administrator](/resource-manager/docs/organization-policy/using-constraints#add-org-policy-admin)
to set a constraint.

## Limitations

Shielded VM isn't supported on
[bare-metal instances](/compute/docs/machine-resource#bare-metal-types) with
the exception of A4X and C4A bare metal instances.

## What's next

- Learn about
[retrieving the endorsement key from the vTPM](/compute/shielded-vm/docs/retrieving-endorsement-key).

- Learn about one approach to
[automating responses to integrity monitoring events](/compute/shielded-vm/docs/automating-responses-integrity-failures).