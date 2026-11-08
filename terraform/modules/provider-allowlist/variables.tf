variable "name" {
  description = "Prefix list name."
  type        = string
}

variable "cidrs_file" {
  description = "Path to a newline-separated CIDR list."
  type        = string
}

variable "address_family" {
  description = "IPv4 or IPv6."
  type        = string
  default     = "IPv4"

  validation {
    condition     = contains(["IPv4", "IPv6"], var.address_family)
    error_message = "address_family must be IPv4 or IPv6."
  }
}

variable "tags" {
  description = "Tags for the prefix list."
  type        = map(string)
  default     = {}
}
